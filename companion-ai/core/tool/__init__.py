from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from core.tool.base import BaseTool, ToolError, ToolFailure, ToolResult

if TYPE_CHECKING:
    from core.tool.ask_human import AskHuman
    from core.tool.computer import ComputerShellTool
    from core.tool.planning import PlanningTool
    from core.tool.terminate import Terminate
    from core.tool.tavily_search import (
        TavilySearchArgs,
        TavilySearchResponse,
        TavilySearchTool,
        tavily_search,
    )

__all__ = [
    "AskHuman",
    "BaseTool",
    "ComputerShellTool",
    "PlanningTool",
    "Terminate",
    "ToolError",
    "ToolFailure",
    "ToolResult",
    "TavilySearchArgs",
    "TavilySearchResponse",
    "TavilySearchTool",
    "tavily_search",
]


def __getattr__(name: str) -> Any:
    if name == "AskHuman":
        from core.tool.ask_human import AskHuman

        return AskHuman
    if name == "ComputerShellTool":
        from core.tool.computer import ComputerShellTool

        return ComputerShellTool
    if name == "PlanningTool":
        from core.tool.planning import PlanningTool

        return PlanningTool
    if name == "Terminate":
        from core.tool.terminate import Terminate

        return Terminate
    if name in {"TavilySearchArgs", "TavilySearchResponse", "TavilySearchTool", "tavily_search"}:
        tavily_search_module = importlib.import_module("core.tool.tavily_search")
        return getattr(tavily_search_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
