"""BaseAgent: state machine + step loop scaffold.

Inspired by OpenManus app/agent/base.py. Adapted to companion-ai:
- LLM client is the project's LLMClient protocol (HTTP)
- Memory is the project's AgentTaskState.messages list (no separate Memory class)
- State machine reuses AgentTaskState.status (running/waiting_human/done/failed)

Subclasses implement ``step()``. The loop drives ``current_step < max_steps``
while ``state.status != "done"``. Detects "stuck" state (duplicate assistant
content) and injects a strategy-change hint into ``next_step_prompt``.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from core.agent.state import AgentTaskState
from core.agent.store import now_iso, save_task
from core.llm.client import HttpLLMClient

logger = logging.getLogger(__name__)


class BaseAgent(BaseModel, ABC):
    """Abstract base class for state-managed step loops."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., description="Unique agent name")
    description: Optional[str] = Field(None, description="Agent description")

    system_prompt: Optional[str] = Field(None)
    next_step_prompt: Optional[str] = Field(None)

    # ``llm`` is typed Any here because ``LLMClient`` is a Protocol — pydantic
    # cannot use protocols for runtime ``isinstance`` validation. We still
    # default to HttpLLMClient and rely on duck typing at call sites.
    llm: Any = Field(default_factory=HttpLLMClient)
    task: AgentTaskState = Field(..., description="Persisted task state (messages + status)")
    session_key: str = Field(..., description="Redis session key for this task")
    timezone_name: str = "Asia/Shanghai"

    max_steps: int = Field(default=8)
    current_step: int = Field(default=0)
    duplicate_threshold: int = 2

    @asynccontextmanager
    async def state_context(self, new_status: str):
        """Run a block under a target task status; on exception flip to failed.

        Mirrors OpenManus app/agent/base.py:58-82 but uses the project's task.status
        field.
        """
        previous = self.task.status
        self.task.status = new_status  # type: ignore[assignment]
        try:
            yield
        except Exception:
            self.task.status = "failed"
            self.task.updated_at = now_iso(self.timezone_name)
            try:
                await save_task(self.session_key, self.task)
            except Exception:  # pragma: no cover
                logger.exception("save_task on failure path failed")
            raise
        finally:
            # Only revert when nothing else (e.g. a subclass) bumped the status.
            if self.task.status == new_status:
                self.task.status = previous  # type: ignore[assignment]

    async def run(self) -> str:
        """Drive step() until done/waiting/max_steps.

        Returns the last step's text output (or empty string if nothing produced).
        Subclasses are responsible for appending the final assistant message; the
        loop does not synthesize one.
        """
        results: list[str] = []
        async with self.state_context("running"):
            while (
                self.current_step < self.max_steps
                and self.task.status not in {"done", "waiting_human"}
            ):
                self.current_step += 1
                logger.info(
                    "[%s] step %d/%d (status=%s)",
                    self.name,
                    self.current_step,
                    self.max_steps,
                    self.task.status,
                )
                step_text = await self.step()
                results.append(step_text)

                if self.is_stuck():
                    self.handle_stuck_state()

            if (
                self.current_step >= self.max_steps
                and self.task.status not in {"done", "waiting_human"}
            ):
                results.append(await self.on_max_steps())
        return "\n".join(r for r in results if r)

    @abstractmethod
    async def step(self) -> str:
        """One unit of work. Subclasses must implement."""

    async def on_max_steps(self) -> str:  # pragma: no cover - optional override
        """Hook fired when the loop exits due to max_steps without finishing."""
        return ""

    # ---- stuck detection -------------------------------------------------

    def is_stuck(self) -> bool:
        """Detect repeated assistant content (likely loop)."""
        messages = self.task.messages
        if len(messages) < 2:
            return False
        last = messages[-1]
        if last.get("role") != "assistant":
            return False
        last_content = last.get("content")
        if not last_content:
            return False
        duplicates = sum(
            1
            for msg in reversed(messages[:-1])
            if msg.get("role") == "assistant" and msg.get("content") == last_content
        )
        return duplicates >= self.duplicate_threshold

    def handle_stuck_state(self) -> None:
        """Append a strategy-change hint to next_step_prompt."""
        hint = (
            "Observed duplicate replies. Try a different approach: "
            "either ask the user for clarification or stop using tools and summarize."
        )
        self.next_step_prompt = (
            f"{hint}\n{self.next_step_prompt}" if self.next_step_prompt else hint
        )
        logger.warning("[%s] stuck detected — injected strategy hint", self.name)

    # ---- memory helpers --------------------------------------------------

    def add_message(self, message: dict[str, Any]) -> None:
        self.task.messages.append(message)

    def add_messages(self, *messages: dict[str, Any]) -> None:
        self.task.messages.extend(messages)
