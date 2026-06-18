"""Tool collection for registering and executing available agent tools."""
from __future__ import annotations

import logging
import time
from typing import Any

from core.tool.base import BaseTool, ToolError, ToolFailure, ToolResult

logger = logging.getLogger(__name__)


class ToolCollection:
    """A collection of defined tools."""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        # 工具名按 lowercase 索引，避免 LLM 偶发的 'Tavily_Search'/'computerShell' 大小写不匹配
        self.tool_map: dict[str, BaseTool] = {tool.name.lower(): tool for tool in tools}

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
        tool = self.tool_map.get((name or "").lower())
        if not tool:
            logger.warning("Tool execution skipped: invalid tool name=%s", name)
            return ToolFailure(error=f"Tool {name} is invalid")
        started = time.perf_counter()
        logger.info("Tool execution started: name=%s", name)
        try:
            result = await tool(**(tool_input or {}))
        except ToolError as e:
            elapsed = time.perf_counter() - started
            logger.warning(
                "Tool execution failed: name=%s elapsed=%.2fs error=%s",
                name,
                elapsed,
                e.message,
            )
            return ToolFailure(error=e.message)
        except TypeError as e:
            # LLM 传错参数（缺必填、多余字段触发 *args 错位）→ 返回 ToolFailure，
            # 不让异常冒泡导致整个 agent turn 挂掉 (AUDIT T-05)。
            elapsed = time.perf_counter() - started
            logger.warning(
                "Tool execution rejected by signature: name=%s elapsed=%.2fs error=%s",
                name,
                elapsed,
                e,
            )
            return ToolFailure(error=f"Invalid tool arguments for {name}: {e}")
        except Exception as e:  # pragma: no cover - 保底兜底
            elapsed = time.perf_counter() - started
            logger.exception(
                "Tool execution crashed: name=%s elapsed=%.2fs", name, elapsed
            )
            return ToolFailure(error=f"Tool {name} crashed: {e}")

        elapsed = time.perf_counter() - started
        error = getattr(result, "error", None)
        if error:
            logger.warning(
                "Tool execution finished with error: name=%s elapsed=%.2fs error=%s",
                name,
                elapsed,
                error,
            )
        else:
            logger.info("Tool execution finished: name=%s elapsed=%.2fs", name, elapsed)
        return result

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
        return self.tool_map.get((name or "").lower())

    def add_tool(self, tool: BaseTool):
        """Add a single tool, skipping duplicate names."""
        key = tool.name.lower()
        if key in self.tool_map:
            logger.warning("Tool %s already exists in collection, skipping", tool.name)
            return self

        self.tools += (tool,)
        self.tool_map[key] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        """Add multiple tools, skipping duplicates."""
        for tool in tools:
            self.add_tool(tool)
        return self
