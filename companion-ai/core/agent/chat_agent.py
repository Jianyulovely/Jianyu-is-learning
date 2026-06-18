"""ChatAgent: companion-ai-flavoured ToolCallAgent.

Extends ToolCallAgent with the shell-confirmation flow that's specific to
companion-ai (computer_shell + one-shot approval token, AUDIT T-03/T-04).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pydantic import Field

from core.agent.helpers import format_final_reply, format_tool_result
from core.agent.toolcall import (
    SHELL_CONFIRMATION_PREFIX,
    SPECIAL_COMPUTER_SHELL,
    ToolCallAgent,
)
from core.llm.client import LLMResult

logger = logging.getLogger(__name__)


class ChatAgent(ToolCallAgent):
    """Adds shell confirmation handling and role-aware final reply formatting."""

    name: str = "chat"
    role_config: dict[str, Any] = Field(default_factory=dict)

    async def _handle_special_tool(
        self,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        result: LLMResult,
    ) -> bool:
        # Defer to parent for ask_human / terminate
        if await super()._handle_special_tool(call_id, name, arguments, result):
            return True

        if name != SPECIAL_COMPUTER_SHELL:
            return False

        # 一次性审批凭证：必须 (command, cwd) 完全一致才放行，命中后立即消费 (AUDIT T-03)
        approved_command = self.task.approved_shell_command
        approved_cwd = self.task.approved_shell_cwd
        request_command = str(arguments.get("command") or "").strip()
        request_cwd_raw = arguments.get("cwd")
        request_cwd = str(request_cwd_raw) if request_cwd_raw is not None else None

        self.task.approved_shell_command = None
        self.task.approved_shell_cwd = None

        if (
            approved_command
            and request_command == approved_command
            and request_cwd == approved_cwd
        ):
            arguments["approved_once"] = True

        tool_result = await self.available_tools.execute(
            name=name, tool_input=arguments
        )
        observation = format_tool_result(tool_result)

        if self._needs_shell_confirmation(tool_result):
            reason = self._shell_confirmation_reason(tool_result)
            self.task.status = "waiting_human"
            self.task.pending_tool_call_id = call_id
            self.task.pending_tool_name = name
            self.task.pending_shell_command = request_command
            self.task.pending_shell_cwd = request_cwd
            self.task.pending_shell_reason = reason
            question = self._build_shell_confirmation_question(
                command=request_command, cwd=request_cwd, reason=reason
            )
            self.task.pending_question = question
            # 写一条 tool 占位响应，使 assistant.tool_calls 序列闭合
            self._append_tool_message(
                call_id=call_id,
                name=name,
                content=f"[awaiting approval] {observation}",
            )
            self.final_reply = question
            return True

        self._append_tool_message(call_id=call_id, name=name, content=observation)
        return True

    # ---- shell-confirm helpers (migrated from agent_service.py) ----------

    @staticmethod
    def _needs_shell_confirmation(tool_result: Any) -> bool:
        error = str(getattr(tool_result, "error", "") or "")
        return error.startswith(SHELL_CONFIRMATION_PREFIX)

    @staticmethod
    def _shell_confirmation_reason(tool_result: Any) -> str:
        error = str(getattr(tool_result, "error", "") or "")
        match = re.search(r"Reason:\s*(.*?)\.\s*Use ask_human", error)
        if match:
            return match.group(1).strip()
        return error or "Command may modify computer state."

    @staticmethod
    def _build_shell_confirmation_question(
        *, command: str, cwd: Optional[str], reason: Optional[str]
    ) -> str:
        location = cwd or "默认项目目录"
        reason_text = reason or "这个命令可能修改电脑状态"
        return (
            "这个命令可能会修改你的电脑，需要你确认后我才执行。\n\n"
            f"目录：{location}\n"
            f"命令：{command}\n"
            f"原因：{reason_text}\n\n"
            "回复“可以”或“确认”后，我只会执行这一条命令。"
        )

    # ---- final-reply formatting -----------------------------------------

    def format_final(self, reply: str | None = None) -> str:
        """Apply role-aware post-processing to the final reply."""
        text = reply if reply is not None else self.final_reply
        return format_final_reply(text or "", self.role_config)
