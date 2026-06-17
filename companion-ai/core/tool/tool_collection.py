"""Tool collection for registering and executing available agent tools."""
from __future__ import annotations

import logging
from typing import Any

from core.tool.base import BaseTool, ToolError, ToolFailure, ToolResult

logger = logging.getLogger(__name__)


class ToolCollection:
    """A collection of defined tools."""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> list[dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    async def execute(
        self,
        *,
        name: str,
        tool_input: dict[str, Any] | None = None,
    ) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        try:
            return await tool(**(tool_input or {}))
        except ToolError as e:
            return ToolFailure(error=e.message)

    async def execute_all(self) -> list[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                results.append(await tool())
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> BaseTool | None:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        """Add a single tool, skipping duplicate names."""
        if tool.name in self.tool_map:
            logger.warning("Tool %s already exists in collection, skipping", tool.name)
            return self

        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        """Add multiple tools, skipping duplicates."""
        for tool in tools:
            self.add_tool(tool)
        return self
