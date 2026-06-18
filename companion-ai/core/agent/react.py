"""ReActAgent: think → act split of step()."""
from __future__ import annotations

from abc import abstractmethod

from core.agent.base import BaseAgent


class ReActAgent(BaseAgent):
    """Decompose ``step()`` into ``think()`` + ``act()``.

    ``think()`` is asked first; if it returns False the act is skipped. This is
    the same shape as OpenManus app/agent/react.py:11-39.
    """

    async def step(self) -> str:
        should_act = await self.think()
        if not should_act:
            return "Thinking complete — no action needed."
        return await self.act()

    @abstractmethod
    async def think(self) -> bool:
        """Decide whether the agent should act next."""

    @abstractmethod
    async def act(self) -> str:
        """Carry out the decided action (usually executing tool_calls)."""
