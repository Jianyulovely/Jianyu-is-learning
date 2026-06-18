"""PlanningFlow: multi-step task orchestration.

Adapted from OpenManus app/flow/planning.py. Each step is dispatched to an
agent picked by step type (``[AGENT_NAME]`` marker in the step text); the
default agent is ChatAgent.

Key differences from OpenManus:
- The plan is persisted inside the project's AgentTaskState (Redis) instead of
  a process-local dict.
- "create plan" is delegated to PlanBuilder.decide / .create_plan (reuses
  existing logic in core/planning/flow.py to avoid double migration).
- Step-level pause: when an agent flips ``task.status`` to ``waiting_human``
  we mark the step blocked and exit the loop (Telegram is async, we can't
  ``input()`` like the CLI does).

Borrowed from OpenManus on this pass:
- ``while True`` auto-advance across steps (no per-step user "continue").
- ``[AGENT_NAME]`` step routing through ``get_executor`` style dispatch.
- Sub-agent ``terminate`` tool causes the whole plan to abort.
- Step prompt embeds the rendered plan so the agent sees overall progress.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable

from core.agent.chat_agent import ChatAgent
from core.agent.helpers import first_user_message, normalize_history, tool_message
from core.agent.state import AgentTaskState
from core.agent.store import delete_task, now_iso, save_task
from core.agent.toolcall import SPECIAL_COMPUTER_SHELL
from core.flow.base import BaseFlow, FlowOutcome
from core.flow.chat import _clear_pending_tool, _replace_or_append_pending_tool_response
from core.flow.router import (
    is_plan_cancel_request,
    is_plan_continue_request,
    is_plan_status_request,
)
from core.planning.flow import PlanningFlow as PlanBuilder
from core.tool.tool_collection import ToolCollection

logger = logging.getLogger(__name__)


# Step type marker: ``[SHELL]`` / ``[CHAT]`` / ``[SEARCH]`` etc. Case-insensitive,
# extracted lowercased to use as a key in the ``agents`` dict (mirrors OpenManus
# app/flow/planning.py:243-247).
_STEP_TYPE_RE = re.compile(r"\[([A-Z_]+)\]")


def _extract_step_type(step_text: str) -> str | None:
    match = _STEP_TYPE_RE.search(step_text)
    return match.group(1).lower() if match else None


# Each builder receives the per-step context and returns a runnable ChatAgent
# subclass. The default builder produces a vanilla ChatAgent; future routes
# can swap in narrower agents (e.g. shell-only, research-only).
AgentBuilder = Callable[..., ChatAgent]


def _default_agent_builder(
    *,
    step_index: int,
    task: AgentTaskState,
    session_key: str,
    step_prompt: str,
    images: list[str],
    role: dict[str, Any],
    timezone_name: str,
    llm: Any,
    available_tools: Any,
) -> ChatAgent:
    return ChatAgent(
        name=f"plan-step-{step_index + 1}",
        llm=llm,
        task=task,
        session_key=session_key,
        timezone_name=timezone_name,
        available_tools=available_tools,
        system_prompt=step_prompt,
        images=images,
        role_config=role.get("config", {}),
    )


class PlanningFlow(BaseFlow):
    """Multi-step planning orchestrator.

    Note: This class shares its name with the older ``core/planning/flow.py``
    PlanBuilder, but at a different abstraction level. The legacy module is
    imported here as ``PlanBuilder`` to handle plan creation and step prompts.
    """

    def __init__(
        self,
        *,
        llm: Any,
        available_tools: ToolCollection,
        is_approval_reply,
        agents: dict[str, AgentBuilder] | None = None,
        plan_builder: PlanBuilder | None = None,
    ) -> None:
        self._llm = llm
        self._available_tools = available_tools
        self._is_approval_reply = is_approval_reply
        # Dict key = step type (lowercase, matches ``[AGENT_NAME]`` in step text).
        # Order matters: the first key is used as the default fallback.
        self._agents: dict[str, AgentBuilder] = agents or {
            "chat": _default_agent_builder,
        }
        self._default_agent_key = next(iter(self._agents))
        self._plan_builder = plan_builder or PlanBuilder(llm)
        # Reused for chat-mode tasks (waiting_human resume, simple turns).
        from core.flow.chat import ChatFlow  # local import avoids circular

        self._chat_flow = ChatFlow(
            llm=llm,
            available_tools=available_tools,
            is_approval_reply=is_approval_reply,
        )

    async def execute(self, *, context: dict[str, Any]) -> FlowOutcome:
        task: AgentTaskState | None = context.get("task")

        # Existing chat-mode task → delegate to ChatFlow (covers waiting_human resume).
        if task and task.mode == "chat":
            return await self._chat_flow.execute(context=context)

        session_key: str = context["session_key"]
        user_message: str = context["user_message"]
        timezone_name: str = context["timezone_name"]
        current_time_iso: str = context["current_time_iso"]
        system_prompt: str = context["system_prompt"]
        images: list[str] = context.get("images") or []
        role: dict[str, Any] = context["role"]
        emotion_tag: str = context.get("emotion_tag", "neutral")

        # ---- resume: control commands first --------------------------
        if task and task.mode == "planning" and task.plan:
            control_reply = await self._maybe_handle_control(
                task, session_key, user_message
            )
            if control_reply is not None:
                return FlowOutcome(reply=control_reply, task=task, write_history=False)

            if task.status in {"running", "waiting_human"}:
                if task.status == "waiting_human":
                    await self._resume_waiting_human(
                        task=task,
                        session_key=session_key,
                        user_message=user_message,
                        current_time_iso=current_time_iso,
                    )
                elif not is_plan_continue_request(user_message):
                    self._append_user_context(task, user_message)
                    task.updated_at = current_time_iso
                    await save_task(session_key, task)

                reply = await self._run_plan_until_pause(
                    task=task,
                    session_key=session_key,
                    role=role,
                    base_system_prompt=system_prompt,
                    timezone_name=timezone_name,
                    images=images,
                )
                history_user_message = (
                    first_user_message(task.messages) or user_message
                )
                return FlowOutcome(
                    reply=reply,
                    task=task,
                    write_history=task.status != "waiting_human",
                    history_user_message=history_user_message,
                )

        # ---- fresh task ---------------------------------------------------
        history = context.get("history_messages") or []
        messages = list(history)
        messages.append({"role": "user", "content": user_message})

        decision = await self._plan_builder.decide(
            user_message=user_message, images=images
        )

        task = AgentTaskState(
            status="running",
            messages=messages,
            started_at=current_time_iso,
            updated_at=current_time_iso,
            initial_emotion_tag=emotion_tag,
        )

        if not decision.needs_plan:
            task.mode = "chat"
            await save_task(session_key, task)
            agent = ChatAgent(
                name="chat",
                llm=self._llm,
                task=task,
                session_key=session_key,
                timezone_name=timezone_name,
                available_tools=self._available_tools,
                system_prompt=system_prompt,
                images=images,
                role_config=role.get("config", {}),
            )
            await agent.run()
            reply = agent.format_final()
            if task.status == "done":
                await delete_task(session_key)
            return FlowOutcome(reply=reply, task=task, write_history=True)

        task.mode = "planning"
        task.plan = await self._plan_builder.create_plan(
            plan_id=f"{session_key}:{int(datetime.now().timestamp())}",
            user_message=user_message,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
            decision=decision,
        )
        await save_task(session_key, task)
        plan_text = self._plan_builder.render_plan(task.plan)
        execution_reply = await self._run_plan_until_pause(
            task=task,
            session_key=session_key,
            role=role,
            base_system_prompt=system_prompt,
            timezone_name=timezone_name,
            images=images,
        )
        reply = f"我会按这个计划推进：\n\n{plan_text}\n\n{execution_reply}"
        return FlowOutcome(
            reply=reply,
            task=task,
            write_history=task.status != "waiting_human",
        )

    # ---- step execution -------------------------------------------------

    async def _run_plan_until_pause(
        self,
        *,
        task: AgentTaskState,
        session_key: str,
        role: dict[str, Any],
        base_system_prompt: str,
        timezone_name: str,
        images: list[str],
    ) -> str:
        """Drive ``task.plan`` step-by-step until done / waiting_human / failed.

        Mirrors OpenManus PlanningFlow.execute()'s ``while True`` loop. Each
        iteration:
          1. find next active step;
          2. run a fresh ChatAgent under a step-specific system prompt;
          3. on success → mark completed, continue;
          4. on waiting_human / failed → mark blocked, break.

        Returns a Telegram-friendly summary that concatenates each step's
        reply with a 【步骤 N】 header.
        """
        if not task.plan:
            return ""

        step_outputs: list[str] = []

        while True:
            step_index = task.plan.next_active_step_index()
            if step_index is None:
                # 所有步骤完成
                task.status = "done"
                task.updated_at = now_iso(timezone_name)
                await save_task(session_key, task)
                summary = self._plan_builder.render_plan(task.plan)
                await delete_task(session_key)
                head = "\n\n".join(step_outputs).strip()
                tail = f"计划已完成。\n\n{summary}"
                return f"{head}\n\n{tail}" if head else tail

            # 标记当前 step 为 in_progress
            task.current_step_index = step_index
            task.plan = self._plan_builder.mark_step_started(
                task.plan,
                step_index=step_index,
                updated_at=now_iso(timezone_name),
            )
            task.status = "running"
            task.updated_at = now_iso(timezone_name)
            await save_task(session_key, task)

            step_prompt = self._plan_builder.build_step_system_prompt(
                base_prompt=base_system_prompt,
                plan=task.plan,
                step_index=step_index,
            )
            # 图片仅在第一个 step 注入，避免后续 step 重复发送同一张图。
            step_images = images if step_index == 0 else []

            # OpenManus 风格的 step type 路由：识别 step 文本里的 [AGENT_NAME] 标记，
            # 在 self._agents 里找对应 builder；未命中时退化到默认 builder。
            step_text = task.plan.steps[step_index].text
            step_type = _extract_step_type(step_text)
            builder = (
                self._agents.get(step_type) if step_type else None
            ) or self._agents[self._default_agent_key]
            agent = builder(
                step_index=step_index,
                task=task,
                session_key=session_key,
                step_prompt=step_prompt,
                images=step_images,
                role=role,
                timezone_name=timezone_name,
                llm=self._llm,
                available_tools=self._available_tools,
            )
            await agent.run()
            step_reply = agent.format_final()
            step_outputs.append(f"【步骤 {step_index + 1}】{step_reply}")

            # 1) waiting_human：等用户审批/澄清，把 step 标 blocked 后中断循环
            if task.status == "waiting_human":
                task.plan = self._plan_builder.mark_step_blocked(
                    task.plan,
                    step_index=step_index,
                    updated_at=now_iso(timezone_name),
                    note=task.pending_question or "Waiting for user input.",
                )
                await save_task(session_key, task)
                progress = (
                    f"\n\n当前进度："
                    f"{task.plan.completed_count()}/{task.plan.total_count()} 步完成。"
                )
                return "\n\n".join(step_outputs).strip() + progress

            # 2) failed：step 执行出错（BaseAgent.state_context 已经标 failed）
            if task.status == "failed":
                task.plan = self._plan_builder.mark_step_blocked(
                    task.plan,
                    step_index=step_index,
                    updated_at=now_iso(timezone_name),
                    note="Step execution failed.",
                )
                await save_task(session_key, task)
                return (
                    "\n\n".join(step_outputs).strip()
                    + "\n\n这一步执行出了点问题，先停在这里。等你看一下。"
                )

            # 3) sub-agent 主动 terminate → 整个 plan 中止（OpenManus 风格）
            if getattr(agent, "terminated", False):
                task.plan = self._plan_builder.mark_step_completed(
                    task.plan,
                    step_index=step_index,
                    updated_at=now_iso(timezone_name),
                    note=step_reply[:300],
                )
                task.current_step_index = None
                task.status = "done"
                task.updated_at = now_iso(timezone_name)
                await save_task(session_key, task)
                await delete_task(session_key)
                tail = (
                    f"\n\n（任务已主动终止）\n\n"
                    f"{self._plan_builder.render_plan(task.plan)}"
                )
                return "\n\n".join(step_outputs).strip() + tail

            # 4) 正常完成 → 标 completed，task.status 重置为 running 准备下一轮
            task.plan = self._plan_builder.mark_step_completed(
                task.plan,
                step_index=step_index,
                updated_at=now_iso(timezone_name),
                note=step_reply[:300],
            )
            task.current_step_index = None
            task.status = "running"
            task.updated_at = now_iso(timezone_name)
            await save_task(session_key, task)
            # 继续 while 自动推进到下一个 step

    # ---- helpers --------------------------------------------------------

    async def _maybe_handle_control(
        self,
        task: AgentTaskState,
        session_key: str,
        user_message: str,
    ) -> str | None:
        if task.plan is None:
            return None
        if task.status == "done":
            return None
        if is_plan_cancel_request(user_message):
            await delete_task(session_key)
            return "已取消当前计划。"
        if is_plan_status_request(user_message):
            return self._plan_builder.render_plan(
                task.plan, current_step_index=task.current_step_index
            )
        return None

    async def _resume_waiting_human(
        self,
        *,
        task: AgentTaskState,
        session_key: str,
        user_message: str,
        current_time_iso: str,
    ) -> None:
        if task.pending_tool_name == SPECIAL_COMPUTER_SHELL:
            approved = self._is_approval_reply(user_message)
            if approved:
                task.approved_shell_command = task.pending_shell_command
                task.approved_shell_cwd = task.pending_shell_cwd
                approval_content = "User approved the pending computer_shell command."
            else:
                approval_content = "User did not approve the pending computer_shell command."
                if task.plan and task.current_step_index is not None:
                    task.plan = self._plan_builder.mark_step_blocked(
                        task.plan,
                        step_index=task.current_step_index,
                        updated_at=now_iso(task.updated_at and "Asia/Shanghai"),
                        note="User declined shell command.",
                    )
        else:
            approval_content = user_message

        _replace_or_append_pending_tool_response(
            task=task,
            approval_content=approval_content,
        )
        task.status = "running"
        _clear_pending_tool(task)
        task.updated_at = current_time_iso
        await save_task(session_key, task)

    def _append_user_context(self, task: AgentTaskState, text: str) -> None:
        content = text.strip()
        if content:
            task.messages.append({"role": "user", "content": content})
