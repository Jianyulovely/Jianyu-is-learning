"""Agent runtime: layered abstractions.

Layers (mirrors OpenManus app/agent/):
- BaseAgent: state machine + run/step loop scaffold
- ReActAgent: think/act split
- ToolCallAgent: LLM-driven tool loop with OpenAI tool_calls protocol
- ChatAgent: companion-ai-flavoured ToolCallAgent (shell confirm + reply format)
"""
from core.agent.base import BaseAgent
from core.agent.chat_agent import ChatAgent
from core.agent.react import ReActAgent
from core.agent.toolcall import (
    SHELL_CONFIRMATION_PREFIX,
    SPECIAL_ASK_HUMAN,
    SPECIAL_COMPUTER_SHELL,
    SPECIAL_TERMINATE,
    ToolCallAgent,
)

__all__ = [
    "BaseAgent",
    "ChatAgent",
    "ReActAgent",
    "ToolCallAgent",
    "SHELL_CONFIRMATION_PREFIX",
    "SPECIAL_ASK_HUMAN",
    "SPECIAL_COMPUTER_SHELL",
    "SPECIAL_TERMINATE",
]
