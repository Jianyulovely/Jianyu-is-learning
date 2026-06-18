"""PlanningFlow routing + terminate semantics (OpenManus parity).

Covers:
- ``[AGENT_NAME]`` step-type routing dispatches to the matching builder
- LLM calling the ``terminate`` tool aborts the whole plan mid-step
- The default builder is used when no ``[AGENT_NAME]`` marker is present
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agent.state import AgentTaskState
from core.agent_service import AgentService
from core.flow.planning import _extract_step_type, _default_agent_builder
from core.llm.client import LLMResult
from core.messaging.models import InboundMessage
from core.planning.models import create_plan_state


NOW = "2026-06-18T10:00:00+08:00"


# ----------------------------------------------------------------------
# Reuse the fakes pattern from test_planning_flow_resume
# ----------------------------------------------------------------------


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def chat(self, payload):
        self.calls.append(payload)
        reply = self.replies.pop(0) if self.replies else "done"
        return LLMResult(reply=reply, tool_calls=[], usage={})


class TerminateLLM:
    """First call emits a terminate tool_call, the rest return final text."""

    def __init__(self):
        self.call_count = 0

    async def chat(self, payload):
        self.call_count += 1
        if self.call_count == 1:
            return LLMResult(
                reply="I have to stop",
                tool_calls=[
                    {
                        "id": "tc-1",
                        "function": {
                            "name": "terminate",
                            "arguments": '{"status": "failure"}',
                        },
                    }
                ],
                usage={},
            )
        return LLMResult(reply="should not be used", tool_calls=[], usage={})


class FakeSession:
    async def ensure_user(self, *args, **kwargs):
        return None

    async def get_user(self, user_id):
        return {"role_id": "Alex", "nickname": "tester"}

    async def get_intimacy(self, user_id):
        return 20

    async def get_history(self, user_id):
        return []

    async def get_last_image_desc(self, user_id):
        return ""

    async def append_message(self, *args, **kwargs):
        return None

    async def bump_intimacy(self, *args, **kwargs):
        return None

    async def update_state(self, *args, **kwargs):
        return None


class FakeTools:
    def to_params(self):
        return []

    async def execute(self, *, name, tool_input):
        return SimpleNamespace(output="", error=None)


class FakeMemoryService:
    async def build_memory_summary(self, ctx):
        return ""


class FakePromptEngine:
    def build_system_prompt(self, ctx):
        return "system prompt"


def make_plan_with_marker():
    return create_plan_state(
        plan_id="plan-route-1",
        title="Routed plan",
        steps=[
            "[SHELL] List files",
            "[SEARCH] Look up lyrics",
            "summarize results",
        ],
        created_at=NOW,
        updated_at=NOW,
    )


def make_task(plan):
    return AgentTaskState(
        status="running",
        mode="planning",
        messages=[{"role": "user", "content": "do the thing"}],
        plan=plan,
        started_at=NOW,
        updated_at=NOW,
    )


def patch_store(monkeypatch, initial_task=None):
    import core.agent_service as agent_service
    import core.agent.store as store_mod
    import core.flow.chat as chat_mod
    import core.flow.planning as planning_mod
    import core.agent.toolcall as toolcall_mod
    import core.agent.base as base_mod

    store = {"task": initial_task, "deleted": False}

    async def fake_load(_):
        return store["task"]

    async def fake_save(_, t):
        store["task"] = t
        store["deleted"] = False

    async def fake_delete(_):
        store["task"] = None
        store["deleted"] = True

    def now_iso(_):
        return NOW

    monkeypatch.setattr(store_mod, "load_task", fake_load)
    monkeypatch.setattr(store_mod, "save_task", fake_save)
    monkeypatch.setattr(store_mod, "delete_task", fake_delete)
    monkeypatch.setattr(store_mod, "now_iso", now_iso)
    for mod in (agent_service, chat_mod, planning_mod, toolcall_mod, base_mod):
        for attr, val in (
            ("load_task", fake_load),
            ("save_task", fake_save),
            ("delete_task", fake_delete),
            ("now_iso", now_iso),
        ):
            if hasattr(mod, attr):
                monkeypatch.setattr(mod, attr, val)
    return store


def message(text: str) -> InboundMessage:
    return InboundMessage(
        channel="telegram",
        chat_id="chat-route",
        sender="123",
        content=text,
    )


# ----------------------------------------------------------------------
# _extract_step_type unit tests
# ----------------------------------------------------------------------


def test_extract_step_type_basic():
    assert _extract_step_type("[SHELL] do something") == "shell"
    assert _extract_step_type("Some prefix [SEARCH] look it up") == "search"
    assert _extract_step_type("no marker here") is None
    assert _extract_step_type("[lower] does not count") is None  # uppercase only
    assert _extract_step_type("[A_B] underscored") == "a_b"


# ----------------------------------------------------------------------
# Step-type routing dispatches to the matching builder
# ----------------------------------------------------------------------


async def test_step_type_routes_to_named_builder(monkeypatch):
    plan = make_plan_with_marker()
    task = make_task(plan)
    patch_store(monkeypatch, task)

    builder_calls: list[str] = []

    def make_recording_builder(label: str):
        def builder(**kwargs):
            builder_calls.append(label)
            return _default_agent_builder(**kwargs)

        return builder

    plan_agents = {
        "chat": make_recording_builder("chat"),
        "shell": make_recording_builder("shell"),
        "search": make_recording_builder("search"),
    }
    service = AgentService(
        session=FakeSession(),
        memory_service=FakeMemoryService(),
        prompt_engine=FakePromptEngine(),
        llm_client=FakeLLM(["shell ok", "search ok", "summary"]),
        available_tools=FakeTools(),
        plan_agents=plan_agents,
    )

    await service.handle(message("continue"))

    # Step 1 → shell, step 2 → search, step 3 has no marker → default ("chat")
    assert builder_calls == ["shell", "search", "chat"]


async def test_step_without_marker_uses_default_builder(monkeypatch):
    plan = create_plan_state(
        plan_id="plan-default",
        title="Default routing",
        steps=["just do it"],
        created_at=NOW,
        updated_at=NOW,
    )
    task = make_task(plan)
    patch_store(monkeypatch, task)

    builder_calls: list[str] = []

    def shell_builder(**kwargs):
        builder_calls.append("shell")
        return _default_agent_builder(**kwargs)

    def default_builder(**kwargs):
        builder_calls.append("default")
        return _default_agent_builder(**kwargs)

    service = AgentService(
        session=FakeSession(),
        memory_service=FakeMemoryService(),
        prompt_engine=FakePromptEngine(),
        llm_client=FakeLLM(["done"]),
        available_tools=FakeTools(),
        plan_agents={"chat": default_builder, "shell": shell_builder},
    )

    await service.handle(message("continue"))
    assert builder_calls == ["default"]


# ----------------------------------------------------------------------
# Terminate aborts the whole plan (OpenManus FINISHED parity)
# ----------------------------------------------------------------------


async def test_terminate_tool_aborts_whole_plan(monkeypatch):
    plan = create_plan_state(
        plan_id="plan-term",
        title="Terminate plan",
        steps=["step A", "step B", "step C"],
        created_at=NOW,
        updated_at=NOW,
    )
    task = make_task(plan)
    store = patch_store(monkeypatch, task)

    # Real ToolCollection so terminate tool is actually invokable
    from core.tool.terminate import Terminate
    from core.tool.tool_collection import ToolCollection

    service = AgentService(
        session=FakeSession(),
        memory_service=FakeMemoryService(),
        prompt_engine=FakePromptEngine(),
        llm_client=TerminateLLM(),
        available_tools=ToolCollection(Terminate()),
    )

    outbound = await service.handle(message("continue"))

    # Plan aborted before reaching step B / C
    assert "任务已主动终止" in outbound.content
    assert store["deleted"] is True
