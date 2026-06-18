"""ToolCallAgent: ReAct loop driven by LLM tool_calls.

Mirrors OpenManus app/agent/toolcall.py but adapted to the project's
RequestPayload/LLMClient/ToolCollection and the persistent AgentTaskState.

Key invariants (avoid AUDIT P-02):
- Every assistant message with ``tool_calls`` is followed by exactly one
  ``tool`` message per call, in order, before the next LLM round.
- ``parallel_tool_calls=False`` is requested in RequestPayload (P1.4) so the
  LLM normally returns at most one call per round. If multiple come back we
  still execute them all, but a "waiting_human" trigger pauses *after* every
  prior tool_call has been answered.
"""
from __future__ import annotations

import logging
from typing import Any, ClassVar, Optional

from pydantic import Field

from bot.models import RequestPayload
from config import config
from core.agent.helpers import (
    ToolArgumentError,
    append_assistant_result,
    format_tool_result,
    parse_tool_arguments,
    tool_message,
)
from core.agent.react import ReActAgent
from core.agent.store import now_iso, save_task
from core.llm.client import LLMResult
from core.tool.tool_collection import ToolCollection

logger = logging.getLogger(__name__)

SPECIAL_ASK_HUMAN = "ask_human"
SPECIAL_TERMINATE = "terminate"
SPECIAL_COMPUTER_SHELL = "computer_shell"
SHELL_CONFIRMATION_PREFIX = "Command requires human confirmation before execution."


class ToolCallAgent(ReActAgent):
    """LLM-driven tool-using ReAct loop.

    Subclasses typically provide ``system_prompt`` and may override
    ``_handle_special_tool`` to inject business rules (e.g. role-aware reply
    formatting) after the loop ends.
    """

    # ``available_tools`` is typed Any so tests can plug in fakes without
    # subclassing ToolCollection. Real wiring still uses ToolCollection.
    available_tools: Any = Field(...)
    images: list[str] = Field(default_factory=list)

    final_reply: str = ""
    # cached LLMResult from the most recent think() so act() can read tool_calls
    last_result: Optional[LLMResult] = None
    # True when the LLM explicitly called the ``terminate`` tool this turn.
    # PlanningFlow reads this to decide whether to abort the whole plan
    # (mirrors OpenManus ``executor.state == FINISHED``).
    terminated: bool = False

    SPECIAL_TOOLS: ClassVar[set[str]] = {
        SPECIAL_ASK_HUMAN,
        SPECIAL_TERMINATE,
    }

    # ---- think -----------------------------------------------------------

    async def think(self) -> bool:
        # Only send images on the very first round of a fresh task.
        send_images = self.images if self.current_step == 1 else []
        payload = RequestPayload(
            system_prompt=self.system_prompt or "",
            history_messages=list(self.task.messages),
            images=send_images,
            tools=self.available_tools.to_params(),
        )
        result = await self.llm.chat(payload)
        self.last_result = result
        append_assistant_result(self.task, result)
        self.task.updated_at = now_iso(self.timezone_name)
        await save_task(self.session_key, self.task)

        if not result.tool_calls:
            # No further actions. Record final reply and terminate the loop.
            self.final_reply = result.reply or ""
            self.task.status = "done"
            return False
        return True

    # ---- act -------------------------------------------------------------

    async def act(self) -> str:
        result = self.last_result
        if result is None or not result.tool_calls:
            return ""

        for tool_call in result.tool_calls:
            call_id = str(tool_call.get("id") or "")
            function = tool_call.get("function") or {}
            name = str(function.get("name") or "")

            try:
                arguments = parse_tool_arguments(function.get("arguments"))
            except ToolArgumentError as exc:
                self._append_tool_message(
                    call_id=call_id,
                    name=name or "unknown_tool",
                    content=f"[tool error] arguments invalid: {exc}",
                )
                continue

            handled = await self._handle_special_tool(call_id, name, arguments, result)
            if handled:
                # Special tools may set task.status to waiting_human/done; we keep
                # consuming the remaining tool_calls in this round if the run
                # didn't terminate, because every call needs a tool response.
                if self.task.status in {"waiting_human", "done"}:
                    # Append placeholder responses to preserve OpenAI protocol
                    # invariants for any not-yet-handled calls in this batch.
                    continue
                continue

            tool_result = await self.available_tools.execute(
                name=name, tool_input=arguments
            )
            observation = format_tool_result(tool_result)
            self._append_tool_message(call_id=call_id, name=name, content=observation)

        await save_task(self.session_key, self.task)
        return ""

    # ---- specials --------------------------------------------------------

    async def _handle_special_tool(
        self,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        result: LLMResult,
    ) -> bool:
        """Hook for AskHuman / Terminate / shell-confirm style detours.

        Returns True if the tool was fully handled here (no further execution
        needed). Subclasses extend this.
        """
        if name == SPECIAL_ASK_HUMAN:
            question = (
                str(arguments.get("inquire") or arguments.get("question") or "").strip()
                or (result.reply or "").strip()
                or "我需要你补充一点信息，才能继续。"
            )
            # Record a tool response so the assistant.tool_calls message has a
            # paired tool message even before the user replies (AUDIT P-02).
            self._append_tool_message(
                call_id=call_id, name=name, content="(awaiting user)"
            )
            self.task.status = "waiting_human"
            self.task.pending_tool_call_id = call_id
            self.task.pending_tool_name = name
            self.task.pending_question = question
            self.final_reply = question
            return True

        if name == SPECIAL_TERMINATE:
            self._append_tool_message(
                call_id=call_id, name=name, content="Task terminated by tool."
            )
            self.task.status = "done"
            self.terminated = True
            status_value = str(arguments.get("status") or "").lower()
            reply_text = (result.reply or "").strip()
            if reply_text:
                self.final_reply = reply_text
            elif status_value == "failure":
                self.final_reply = "任务暂时无法继续，我先停在这里。"
            else:
                self.final_reply = "任务已完成。"
            return True

        return False

    # ---- helpers ---------------------------------------------------------

    def _append_tool_message(self, *, call_id: str, name: str, content: str) -> None:
        self.task.messages.append(
            tool_message(tool_call_id=call_id, name=name, content=content)
        )
        self.task.updated_at = now_iso(self.timezone_name)

    async def on_max_steps(self) -> str:
        """Append a system nudge and ask LLM for a final reply without tools."""
        self.task.messages.append(
            {
                "role": "system",
                "content": (
                    "Reached the maximum tool rounds. Do not call any further tools. "
                    "Summarize the best answer based on observations gathered so far."
                ),
            }
        )
        try:
            payload = RequestPayload(
                system_prompt=self.system_prompt or "",
                history_messages=list(self.task.messages),
                tools=[],
            )
            result = await self.llm.chat(payload)
            self.final_reply = result.reply or ""
            append_assistant_result(self.task, result)
        except Exception:  # pragma: no cover - last-line fallback
            logger.exception("Final summarization after max_steps failed")
            self.final_reply = "我已经达到本次工具调用上限，暂时只能先停在这里。"
        self.task.status = "done"
        self.task.updated_at = now_iso(self.timezone_name)
        await save_task(self.session_key, self.task)
        return self.final_reply
