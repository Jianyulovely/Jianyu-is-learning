"""ToolCollection + helpers regression tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agent.helpers import (
    MAX_OBSERVATION_CHARS,
    ToolArgumentError,
    format_tool_result,
    parse_tool_arguments,
)
from core.tool.base import BaseTool, ToolFailure, ToolResult
from core.tool.tool_collection import ToolCollection


# -----------------------------------------------------------------------
# Fakes
# -----------------------------------------------------------------------


class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Echo back the input."
    parameters: dict = {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, *, text: str = "") -> ToolResult:
        return self.success_response(text or "")


class StrictTool(BaseTool):
    name: str = "strict"
    description: str = "Requires a 'must' kwarg."
    parameters: dict = {"type": "object", "properties": {}}

    async def execute(self, *, must: str) -> ToolResult:
        return self.success_response(must)


# -----------------------------------------------------------------------
# parse_tool_arguments (AUDIT T-05)
# -----------------------------------------------------------------------


def test_parse_arguments_accepts_dict():
    assert parse_tool_arguments({"a": 1}) == {"a": 1}


def test_parse_arguments_accepts_empty():
    assert parse_tool_arguments(None) == {}
    assert parse_tool_arguments("") == {}


def test_parse_arguments_raises_on_invalid_json():
    with pytest.raises(ToolArgumentError):
        parse_tool_arguments("not json")


def test_parse_arguments_raises_on_non_object_json():
    with pytest.raises(ToolArgumentError):
        parse_tool_arguments("[1, 2, 3]")


# -----------------------------------------------------------------------
# format_tool_result truncation (AUDIT T-07)
# -----------------------------------------------------------------------


def test_format_tool_result_passthrough_short():
    r = ToolResult(output="short text")
    assert format_tool_result(r) == "short text"


def test_format_tool_result_truncates_long_output():
    big = "x" * (MAX_OBSERVATION_CHARS + 1000)
    r = ToolResult(output=big)
    out = format_tool_result(r)
    assert len(out) < len(big)
    assert "truncated" in out


def test_format_tool_result_includes_error_prefix():
    r = ToolFailure(error="boom")
    assert format_tool_result(r).startswith("[tool error]")


# -----------------------------------------------------------------------
# ToolCollection: case-insensitive lookup (T-06) + TypeError tolerance (T-05)
# -----------------------------------------------------------------------


@pytest.mark.asyncio_compatible
async def test_tool_collection_lookup_case_insensitive():
    col = ToolCollection(EchoTool())
    res = await col.execute(name="Echo", tool_input={"text": "hi"})
    assert res.error is None
    assert res.output == "hi"


async def test_tool_collection_unknown_tool_returns_failure():
    col = ToolCollection(EchoTool())
    res = await col.execute(name="nope", tool_input={})
    assert isinstance(res, ToolFailure)
    assert "invalid" in (res.error or "")


async def test_tool_collection_typeerror_becomes_failure():
    col = ToolCollection(StrictTool())
    # Missing required ``must`` kwarg → TypeError; collection wraps to ToolFailure.
    res = await col.execute(name="strict", tool_input={"other": 1})
    assert isinstance(res, ToolFailure)
    assert "Invalid tool arguments" in (res.error or "")
