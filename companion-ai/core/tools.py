from __future__ import annotations

import logging
from typing import Any

from core.tool.tavily_search import TavilySearchTool

logger = logging.getLogger(__name__)

_TOOLS = {
    TavilySearchTool().name: TavilySearchTool(),
}


async def select_tools(user_message: str) -> list[dict[str, Any]]:
    text = user_message.lower()
    realtime_markers = (
        "最新",
        "今天",
        "现在",
        "新闻",
        "搜索",
        "查一下",
        "联网",
        "latest",
        "today",
        "news",
        "search",
    )
    if any(marker in text for marker in realtime_markers):
        return [_TOOLS["tavily_search"].to_param()]
    return []


async def execute_tool(name: str, tool_input: dict[str, Any] | None = None) -> str:
    tool = _TOOLS.get(name)
    if tool is None:
        return f"[tool error] Unknown tool: {name}"

    result = await tool.execute(**(tool_input or {}))
    if getattr(result, "error", None):
        return f"[tool error] {result.error}"
    return str(getattr(result, "output", result))
