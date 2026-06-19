"""Tests for the planning router heuristics + LLM-driven decide.

Covers the 2026-06-18 regression: "在 D:\\data 这个路径下给我写一个 txt 文件"
must NOT trigger planning (single-step task) and the LLM-driven path must
not fall back to a generic template when the LLM produces no plan tool_call.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm.client import LLMResult
from core.planning.flow import PlanningFlow as PlanBuilder


# -----------------------------------------------------------------------
# _looks_complex (the cheap heuristic gate)
# -----------------------------------------------------------------------


@pytest.fixture
def builder():
    return PlanBuilder(llm_client=None)  # _looks_complex doesn't touch llm


@pytest.mark.parametrize(
    "msg",
    [
        # Single-step asks (used to wrongly trigger plan)
        "在 D:\\data 这个路径下给我写一个txt文件",
        "查一下今天天气",
        "帮我写一个 hello world",
        "把这个文件读出来",
        "在桌面建一个 todo.txt",
        "ls 这个目录",
        "今年世界杯主题曲是什么",
        # Conversational
        "你好",
        "怎么样",
        "今天累死了",
    ],
)
def test_single_step_messages_dont_look_complex(builder, msg):
    assert builder._looks_complex(msg, []) is False, msg


@pytest.mark.parametrize(
    "msg",
    [
        # Explicit multi-step verbiage
        "先查一下歌词，然后写到 D:\\data 下",
        "帮我先建文件夹，然后写文件，最后 commit",
        "step by step explain how X works",
        "first download then extract then move",
        # Explicit "plan" keyword
        "帮我做个计划",
        "给我一个步骤清单",
        "make me a plan to learn rust",
        # Batch operations
        "批量重命名这些图片",
        "逐个检查这些文件",
        # Long messages (≥ 80 chars)
        "x" * 80,
    ],
)
def test_multi_step_messages_look_complex(builder, msg):
    assert builder._looks_complex(msg, []) is True, msg


def test_two_or_more_images_look_complex(builder):
    assert builder._looks_complex("test", ["a", "b"]) is True
    # one image alone is not enough; ChatFlow can describe it
    assert builder._looks_complex("test", ["a"]) is False


# -----------------------------------------------------------------------
# decide() goes through the LLM tool_call path
# -----------------------------------------------------------------------


class StubLLM:
    """Returns a programmed sequence of LLMResults to ``chat`` calls."""

    def __init__(self, *results: LLMResult):
        self.queue = list(results)
        self.calls = []

    async def chat(self, payload):
        self.calls.append(payload)
        if self.queue:
            return self.queue.pop(0)
        return LLMResult(reply="", tool_calls=[], usage={})


def planning_tool_call(steps, title="My plan"):
    """Build a fake assistant tool_call invoking the planning tool."""
    return {
        "id": "call-1",
        "function": {
            "name": "planning",
            "arguments": json.dumps(
                {
                    "command": "create",
                    "plan_id": "router",
                    "title": title,
                    "steps": steps,
                }
            ),
        },
    }


async def test_decide_returns_no_plan_when_heuristic_says_no():
    # 哪怕给个 LLM 也不会被调用，因为 _looks_complex=False
    llm = StubLLM(LLMResult(reply="should not be called", tool_calls=[], usage={}))
    builder = PlanBuilder(llm_client=llm)

    decision = await builder.decide(user_message="写一个 hello.txt", images=[])

    assert decision.needs_plan is False
    assert decision.steps == []
    assert llm.calls == []  # LLM 不被调用


async def test_decide_returns_no_plan_when_llm_emits_no_tool_call():
    # 复杂消息触发 _looks_complex → LLM 被询问，但回了纯文本（"不需要 plan"）
    llm = StubLLM(
        LLMResult(reply="No plan needed; this is one tool call.", tool_calls=[], usage={})
    )
    builder = PlanBuilder(llm_client=llm)

    decision = await builder.decide(
        user_message="先查歌词，然后写到 D:\\data 下面",
        images=[],
    )

    assert decision.needs_plan is False
    assert decision.steps == []
    assert len(llm.calls) == 1  # LLM 被询问过


async def test_decide_returns_plan_when_llm_emits_tool_call():
    llm = StubLLM(
        LLMResult(
            reply="",
            tool_calls=[
                planning_tool_call(
                    steps=[
                        "[SEARCH] look up lyrics",
                        "write file to D:\\data\\song.txt",
                        "verify file content",
                    ],
                    title="Write lyrics",
                )
            ],
            usage={},
        )
    )
    builder = PlanBuilder(llm_client=llm)

    decision = await builder.decide(
        user_message="先查歌词，然后写到 D:\\data 下面",
        images=[],
    )

    assert decision.needs_plan is True
    assert decision.title == "Write lyrics"
    assert decision.steps == [
        "[SEARCH] look up lyrics",
        "write file to D:\\data\\song.txt",
        "verify file content",
    ]


async def test_decide_no_fallback_template_when_llm_call_fails():
    """Critical regression guard for the 2026-06-18 incident.

    The old impl called the LLM in JSON-mode and, on any exception, returned
    the generic ``["Clarify…", "Execute…", "Verify…"]`` template. The agent
    then ran the whole task 3x. We now return needs_plan=False on failure.
    """

    class FailingLLM:
        async def chat(self, payload):
            raise RuntimeError("LLM is unavailable")

    builder = PlanBuilder(llm_client=FailingLLM())

    decision = await builder.decide(
        user_message="先做 A 然后做 B 最后做 C",
        images=[],
    )

    assert decision.needs_plan is False
    assert decision.steps == []


async def test_decide_no_plan_when_tool_call_has_no_steps():
    llm = StubLLM(
        LLMResult(
            reply="",
            tool_calls=[
                {
                    "id": "call-1",
                    "function": {
                        "name": "planning",
                        "arguments": json.dumps(
                            {"command": "create", "plan_id": "router", "title": "x", "steps": []}
                        ),
                    },
                }
            ],
            usage={},
        )
    )
    builder = PlanBuilder(llm_client=llm)

    decision = await builder.decide(user_message="批量重命名图片", images=[])

    assert decision.needs_plan is False
