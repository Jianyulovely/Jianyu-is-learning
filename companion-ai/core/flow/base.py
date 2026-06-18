"""BaseFlow: orchestrates one conversation turn.

Inspired by OpenManus app/flow/base.py but stays close to companion-ai's
shape: each Flow takes a fully-prepared inbound context (user message,
system prompt, role, emotion, image context, persisted task) and returns
a final reply string + the post-state of the task.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.agent.state import AgentTaskState


@dataclass
class FlowOutcome:
    """Result of a single Flow.execute() call.

    Attributes:
        reply: the user-visible string the bot should send
        task: the persisted task state at the end of the turn
        write_history: whether to append (user_message, reply) to session.history
        history_user_message: the user message to log (may differ from current
            input when resuming a long task)
    """

    reply: str
    task: AgentTaskState
    write_history: bool = True
    history_user_message: str | None = None


class BaseFlow(ABC):
    """A Flow is a turn-level orchestrator. One Flow per conversation turn."""

    @abstractmethod
    async def execute(self, *, context: dict[str, Any]) -> FlowOutcome:
        """Run the flow.

        ``context`` keys (mirrors AgentService prepared context):
            - user_id: int
            - user_message: str
            - role: dict (loaded role config)
            - emotion_tag: str
            - prompt_image_context: str
            - current_time_iso: str
            - timezone_name: str
            - system_prompt: str
            - images: list[str]
            - task: AgentTaskState | None (existing task, if any)
            - session_key: str
        """
