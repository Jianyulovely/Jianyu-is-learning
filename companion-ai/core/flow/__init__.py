"""Flow layer: turn orchestration that selects and drives agents.

Layers (mirrors OpenManus app/flow/):
- BaseFlow: holds agent registry, exposes ``execute(InboundMessage)``
- ChatFlow: single-agent ReAct loop for casual conversation
- PlanningFlow: multi-step plan executor that dispatches each step to an agent
- router: lightweight control-command detection (cancel/continue/status)

AgentService selects which Flow to use per turn; Flows own the conversation
state machine and call into ChatAgent / future RouterAgent / etc.
"""
from core.flow.base import BaseFlow, FlowOutcome
from core.flow.chat import ChatFlow
from core.flow.planning import AgentBuilder, PlanningFlow

__all__ = [
    "AgentBuilder",
    "BaseFlow",
    "ChatFlow",
    "FlowOutcome",
    "PlanningFlow",
]
