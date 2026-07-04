from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from bot.models import RequestPayload
from core.planning.formatter import format_plan_text, format_step_update
from core.planning.models import (
    PlanState,
    create_plan_state,
    mark_plan_step,
)
from core.tool.planning import PlanningTool

logger = logging.getLogger(__name__)


@dataclass
class PlanningDecision:
    needs_plan: bool
    title: str
    steps: list[str]
    rationale: str = ""


class PlanningFlow:
    def __init__(self, llm_client) -> None:
        self._llm_client = llm_client
        self._planning_tool = PlanningTool()

    async def decide(
        self,
        *,
        user_message: str,
        images: list[str] | None = None,
    ) -> PlanningDecision:
        """Decide whether the user request warrants an explicit multi-step plan.

        Two-stage:

        1. ``_looks_complex`` is a fast keyword/length heuristic; if it says
           "obviously single-step" we exit immediately with ``needs_plan=False``.
        2. Otherwise we ask the LLM to either return a ``planning.create``
           tool_call (= "yes, plan, here are the steps") or a plain text
           reply (= "no plan needed"). Mirrors OpenManus
           ``_create_initial_plan`` (app/flow/planning.py:170-198).

        Either path failing → ``needs_plan=False``. Crucially we no longer fall
        back to a generic ``["Clarify…", "Execute…", "Verify…"]`` template:
        that template confused the agent into doing the whole task three times
        (see user report 2026-06-18). When in doubt, ChatFlow handles it.
        """
        images = images or []
        if not self._looks_complex(user_message, images):
            return PlanningDecision(needs_plan=False, title="", steps=[])

        system_prompt = (
            "You are a planning router. Decide whether the user's request needs "
            "an explicit multi-step plan that should be tracked step-by-step.\n"
            "\n"
            "A plan is appropriate ONLY when:\n"
            "  - the task has 3+ independent actions that benefit from progress tracking\n"
            "  - the actions need to happen in a specific order\n"
            "  - the user explicitly asked for a plan / multi-step breakdown\n"
            "\n"
            "A plan is NOT appropriate (and you should reply with plain text, no tool call) when:\n"
            "  - the task is one tool call (write one file, look up one fact)\n"
            "  - the task is conversational\n"
            "  - the task is ambiguous (better to ask the user via the main agent)\n"
            "\n"
            "If a plan IS needed: call the `planning` tool with command='create', "
            "plan_id='router' (will be replaced), title=<short title>, "
            "steps=[<3 to 7 concrete actions the agent can execute with str_replace_editor / "
            "computer_shell / tavily_search>]. Do NOT include manual or GUI actions. "
            "You may optionally prefix a step with [SHELL] or [SEARCH] to hint executor type.\n"
            "\n"
            "If NO plan is needed: reply with one short sentence (no tool call)."
        )
        request = (
            f"User request: {user_message}\n"
            f"Has images: {bool(images)}"
        )

        try:
            result = await self._llm_client.chat(
                RequestPayload(
                    system_prompt=system_prompt,
                    history_messages=[{"role": "user", "content": request}],
                    tools=[self._planning_tool.to_param()],
                )
            )
        except Exception as exc:
            logger.warning("planning decision LLM call failed: %s", exc)
            return PlanningDecision(needs_plan=False, title="", steps=[])

        if not result.tool_calls:
            # LLM 决定不拆 plan → 走 ChatFlow
            return PlanningDecision(needs_plan=False, title="", steps=[])

        for tool_call in result.tool_calls:
            function = tool_call.get("function") or {}
            if function.get("name") != "planning":
                continue
            args_raw = function.get("arguments") or {}
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    logger.warning(
                        "planning tool_call arguments not JSON: %r", args_raw
                    )
                    continue
            elif isinstance(args_raw, dict):
                args = args_raw
            else:
                continue

            if args.get("command") != "create":
                continue
            raw_steps = args.get("steps") or []
            steps = [
                str(s).strip() for s in raw_steps if isinstance(s, str) and str(s).strip()
            ]
            if not steps:
                continue
            title = str(args.get("title") or "").strip() or self._default_title(user_message)
            rationale = str(args.get("rationale") or "")
            return PlanningDecision(
                needs_plan=True,
                title=title,
                steps=steps[:7],
                rationale=rationale,
            )

        # tool_call 不规范 → 不进 plan
        return PlanningDecision(needs_plan=False, title="", steps=[])

    async def create_plan(
        self,
        *,
        plan_id: str,
        user_message: str,
        current_time_iso: str,
        timezone_name: str,
        decision: PlanningDecision,
    ) -> PlanState:
        return create_plan_state(
            plan_id=plan_id,
            title=decision.title,
            steps=decision.steps,
            created_at=current_time_iso,
            updated_at=current_time_iso,
        )

    def render_plan(self, plan: PlanState, *, current_step_index: int | None = None) -> str:
        return format_plan_text(plan, current_step_index=current_step_index)

    def mark_step_started(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="in_progress",
            updated_at=updated_at,
        )

    def mark_step_completed(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
        note: str = "",
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="completed",
            step_notes=note or None,
            updated_at=updated_at,
        )

    def mark_step_blocked(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
        note: str = "",
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="blocked",
            step_notes=note or None,
            updated_at=updated_at,
        )

    def build_step_system_prompt(
        self,
        *,
        base_prompt: str,
        plan: PlanState,
        step_index: int,
    ) -> str:
        step = plan.steps[step_index]
        return (
            base_prompt
            + "\n\nYou are executing a structured plan.\n"
            + "Only work on the current step below.\n"
            + "Do not skip ahead.\n"
            + "If the current step's intended action has already been completed in "
              "previous steps (visible in the conversation history above), do NOT redo "
              "the work — briefly confirm completion and return.\n"
            + "For local file creation, reading, or editing: use the str_replace_editor tool "
              "with structured arguments. Do NOT build PowerShell Set-Content / Out-File / "
              "redirect commands — they cause encoding and quoting failures.\n"
            + "If the step requires shell-only work (list directories, run git, pip, npm), "
              "use computer_shell.\n"
            + "After writing a file, verify it with str_replace_editor command='view'.\n"
            + "If a tool fails because the path is outside allowed roots, or because "
              "user input was ambiguous, use ask_human — do NOT silently retry with a "
              "different path.\n"
            + "If you need the user to clarify something, use ask_human.\n"
            + "If the whole plan cannot proceed at all (missing prerequisites, "
              "permission denied, irrecoverable error), call terminate(status='failure') "
              "to abort the entire plan instead of carrying on.\n"
            + "If the step is done, return a concise outcome.\n\n"
            + f"Current plan:\n{self.render_plan(plan, current_step_index=step_index)}\n\n"
            + f"Current step:\n{step_index + 1}. {step.text}\n"
        )

    def format_step_progress(
        self,
        plan: PlanState,
        *,
        step_index: int,
        prefix: str = "Progress: ",
    ) -> str:
        return format_step_update(plan, step_index=step_index, prefix=prefix)

    def _default_title(self, user_message: str) -> str:
        text = user_message.strip()
        if len(text) > 20:
            return f"Plan for: {text[:20]}"
        return f"Plan for: {text}"

    def _looks_complex(self, user_message: str, images: list[str]) -> bool:
        """
        快速判断：用户请求内容是否有多步骤关键词或者输入为长指令
        """
        text = user_message.strip()
        if not text:
            return False
        # 显式多步骤连接词：用户主动说"先 X 然后 Y"
        multi_step_markers = (
            "先", "然后", "之后", "接着", "再来", "分别", "依次",
            "批量", "逐个", "所有",
            "step by step", "first ", " then ", "after that",
        )
        if any(marker in text for marker in multi_step_markers):
            return True
        # 用户显式提到 plan / 步骤 / 任务规划
        explicit_planning = ("计划", "步骤", "规划", "plan", "steps")
        if any(kw in text.lower() for kw in explicit_planning):
            return True
        # 多图片输入（图像理解任务通常需要 plan）
        if len(images) >= 2:
            return True
        # 长指令（80+ 字符）通常隐含多步
        if len(text) >= 80:
            return True
        return False
