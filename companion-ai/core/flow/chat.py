"""ChatFlow: single ChatAgent for a casual or single-task conversation turn.

Handles fresh tasks and waiting_human resumption (shell approval, ask_human).
"""
from __future__ import annotations

import logging
from typing import Any

from core.agent.chat_agent import ChatAgent
from core.agent.helpers import first_user_message, tool_message
from core.agent.state import AgentTaskState
from core.agent.store import delete_task, now_iso, save_task
from core.agent.toolcall import SPECIAL_COMPUTER_SHELL
from core.flow.base import BaseFlow, FlowOutcome
from core.tool.tool_collection import ToolCollection

logger = logging.getLogger(__name__)


class ChatFlow(BaseFlow):
    def __init__(
        self,
        *,
        llm: Any,
        available_tools: ToolCollection,
        is_approval_reply,
    ) -> None:
        self._llm = llm
        self._available_tools = available_tools
        # Injected so unit tests can swap approval semantics without rebuilding.
        self._is_approval_reply = is_approval_reply

    async def execute(self, *, context: dict[str, Any]) -> FlowOutcome:
        task: AgentTaskState | None = context.get("task")
        session_key: str = context["session_key"]
        user_message: str = context["user_message"]
        timezone_name: str = context["timezone_name"]
        current_time_iso: str = context["current_time_iso"]
        system_prompt: str = context["system_prompt"]
        images: list[str] = context.get("images") or []
        role: dict[str, Any] = context["role"]

        # ---- resume path: existing waiting_human task --------------------
        if task and task.status == "waiting_human":
            resumed_reply = await self._resume_waiting_human(
                task=task,
                session_key=session_key,
                user_message=user_message,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )
            if resumed_reply is not None:
                return FlowOutcome(
                    reply=resumed_reply,
                    task=task,
                    write_history=True,
                    history_user_message=first_user_message(task.messages) or user_message,
                )

        # ---- fresh task --------------------------------------------------
        if task is None:
            history = context.get("history_messages") or []
            messages = list(history)
            messages.append({"role": "user", "content": user_message})
            task = AgentTaskState(
                status="running",
                mode="chat",
                messages=messages,
                started_at=current_time_iso,
                updated_at=current_time_iso,
                initial_emotion_tag=context.get("emotion_tag"),
            )
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

    async def _resume_waiting_human(
        self,
        *,
        task: AgentTaskState,
        session_key: str,
        user_message: str,
        current_time_iso: str,
        timezone_name: str,
    ) -> str | None:
        """Handle a user reply that resolves a pending tool wait."""
        if task.pending_tool_name == SPECIAL_COMPUTER_SHELL:
            approved = self._is_approval_reply(user_message)
            if approved:
                task.approved_shell_command = task.pending_shell_command
                task.approved_shell_cwd = task.pending_shell_cwd
                approval_content = "User approved the pending computer_shell command."
            else:
                approval_content = "User did not approve the pending computer_shell command."
        else:
            approved = False
            approval_content = user_message

        # Replace the placeholder tool response we appended at pause time
        # (matches the assistant.tool_calls id for OpenAI protocol).
        _replace_or_append_pending_tool_response(
            task=task,
            approval_content=approval_content,
        )

        if task.pending_tool_name == SPECIAL_COMPUTER_SHELL and not approved:
            # 不再立即 delete_task：给 LLM 留一条 reject 痕迹，再让其改路径（AUDIT P-07）。
            task.status = "running"
            _clear_pending_tool(task)
            task.updated_at = current_time_iso
            await save_task(session_key, task)
            # 单独追加一句 system，指引 LLM 选择其他方案
            task.messages.append(
                {
                    "role": "system",
                    "content": (
                        "The user declined the previous shell command. "
                        "Suggest an alternative plan in natural language; "
                        "do not call computer_shell with the same command again."
                    ),
                }
            )
            return None  # 落入主 execute() 的 agent.run()

        task.status = "running"
        _clear_pending_tool(task)
        task.updated_at = current_time_iso
        await save_task(session_key, task)
        return None


def _replace_or_append_pending_tool_response(
    *, task: AgentTaskState, approval_content: str
) -> None:
    """Find the placeholder tool message for pending_tool_call_id and replace its
    content with the resolved approval text. If no placeholder exists, append a new
    tool message so the protocol stays valid.
    """
    pending_id = task.pending_tool_call_id or ""
    pending_name = task.pending_tool_name or "ask_human"
    for message in reversed(task.messages):
        if (
            message.get("role") == "tool"
            and message.get("tool_call_id") == pending_id
        ):
            message["content"] = approval_content
            return
    task.messages.append(
        tool_message(
            tool_call_id=pending_id,
            name=pending_name,
            content=approval_content,
        )
    )


def _clear_pending_tool(task: AgentTaskState) -> None:
    task.pending_tool_call_id = None
    task.pending_tool_name = None
    task.pending_question = None
    task.pending_shell_command = None
    task.pending_shell_cwd = None
    task.pending_shell_reason = None
