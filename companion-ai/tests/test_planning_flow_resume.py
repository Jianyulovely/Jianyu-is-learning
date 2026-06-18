"""End-to-end tests for the planning flow via AgentService.handle().

Migrated from the legacy ``_run_planning_flow`` direct-call test set after
P3 introduced the Flow layer. Tests still feed InboundMessages through the
public ``AgentService.handle`` API; internal store/task access is patched.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agent.state import AgentTaskState
from core.agent_service import AgentService
from core.llm.client import LLMResult
from core.messaging.models import InboundMessage
from core.planning.models import create_plan_state


NOW = "2026-06-18T10:00:00+08:00"


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------


class FakeLLM:
    def __init__(self, replies: list[str]) -> None:
        # Each reply maps to one LLMClient.chat() call. tool_calls is always [].
        self.replies = list(replies)
        self.calls: list = []

    async def chat(self, payload):
        self.calls.append(payload)
        reply = self.replies.pop(0) if self.replies else "done"
        return LLMResult(reply=reply, tool_calls=[], usage={})


class FakeSession:
    def __init__(self) -> None:
        self.history: list[tuple[int, str, str]] = []

    async def ensure_user(self, user_id, username="", role_id="Alex"):
        return None

    async def get_user(self, user_id):
        return {"role_id": "Alex", "nickname": "tester"}

    async def get_intimacy(self, user_id):
        return 20

    async def get_history(self, user_id):
        return []

    async def get_last_image_desc(self, user_id):
        return ""

    async def append_message(self, user_id, role, content, emotion_tag="neutral"):
        self.history.append((user_id, role, content))

    async def bump_intimacy(self, user_id, emotion_tag):
        return None

    async def update_state(self, user_id, **kwargs):
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


# ----------------------------------------------------------------------
# Test helpers
# ----------------------------------------------------------------------


def make_service(replies: list[str]) -> AgentService:
    return AgentService(
        session=FakeSession(),
        memory_service=FakeMemoryService(),
        prompt_engine=FakePromptEngine(),
        llm_client=FakeLLM(replies),
        available_tools=FakeTools(),
    )


def make_plan(step_count: int = 3):
    return create_plan_state(
        plan_id="plan-1",
        title="Test plan",
        steps=[f"step {i + 1}" for i in range(step_count)],
        created_at=NOW,
        updated_at=NOW,
    )


def make_task(*, status: str = "running", step_count: int = 3) -> AgentTaskState:
    return AgentTaskState(
        status=status,
        mode="planning",
        messages=[{"role": "user", "content": "original task"}],
        plan=make_plan(step_count),
        started_at=NOW,
        updated_at=NOW,
    )


def patch_store(monkeypatch, initial_task=None):
    """Patch the shared task store used by both ChatFlow and PlanningFlow."""
    import core.agent_service as agent_service
    import core.agent.store as store_mod
    import core.flow.chat as chat_mod
    import core.flow.planning as planning_mod
    import core.agent.toolcall as toolcall_mod
    import core.agent.base as base_mod

    store = {"task": initial_task, "deleted": False}

    async def fake_load_task(session_key):
        return store["task"]

    async def fake_save_task(session_key, task):
        store["task"] = task
        store["deleted"] = False

    async def fake_delete_task(session_key):
        store["task"] = None
        store["deleted"] = True

    def now_iso(timezone_name):
        return NOW

    monkeypatch.setattr(store_mod, "load_task", fake_load_task)
    monkeypatch.setattr(store_mod, "save_task", fake_save_task)
    monkeypatch.setattr(store_mod, "delete_task", fake_delete_task)
    monkeypatch.setattr(store_mod, "now_iso", now_iso)

    # Each module imported them by-name; patch the re-bound symbols too.
    for mod in (agent_service, chat_mod, planning_mod, toolcall_mod, base_mod):
        for attr, val in (
            ("load_task", fake_load_task),
            ("save_task", fake_save_task),
            ("delete_task", fake_delete_task),
            ("now_iso", now_iso),
        ):
            if hasattr(mod, attr):
                monkeypatch.setattr(mod, attr, val)
    return store


def message(text: str) -> InboundMessage:
    return InboundMessage(
        channel="telegram",
        chat_id="chat-1",
        sender="123",
        content=text,
    )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


async def test_continue_message_advances_plan_to_completion(monkeypatch):
    """PlanningFlow auto-advances through every remaining step in one turn.

    Migrated from the old `_run_one_step` test which only advanced a single
    step; the new flow drives the loop end-to-end (mirrors OpenManus
    PlanningFlow.execute's ``while True``).
    """
    task = make_task()  # 3 steps
    task.plan.steps[0].status = "completed"
    store = patch_store(monkeypatch, task)
    service = make_service(["step 2 result", "step 3 result"])

    outbound = await service.handle(message("continue"))

    assert "step 2 result" in outbound.content
    assert "step 3 result" in outbound.content
    assert "计划已完成" in outbound.content
    # task is deleted at end of plan
    assert store["deleted"] is True
    # "continue" must not be appended as supplemental context
    user_messages = [m["content"] for m in task.messages if m["role"] == "user"]
    assert user_messages == ["original task"]


async def test_supplemental_message_is_appended_and_advances_plan(monkeypatch):
    task = make_task()
    task.plan.steps[0].status = "completed"
    store = patch_store(monkeypatch, task)
    service = make_service(["step 2 with context", "step 3 with context"])

    outbound = await service.handle(message("Supplement: prioritize Windows"))

    assert "step 2 with context" in outbound.content
    assert "step 3 with context" in outbound.content
    assert {
        "role": "user",
        "content": "Supplement: prioritize Windows",
    } in task.messages
    # all 3 steps completed in one turn
    assert store["deleted"] is True


async def test_plan_status_does_not_advance_plan(monkeypatch):
    task = make_task()
    task.plan.steps[0].status = "completed"
    store = patch_store(monkeypatch, task)
    service = make_service(["should not be used"])

    outbound = await service.handle(message("status"))

    assert "Progress: 1/3 steps completed" in outbound.content
    assert store["task"].plan.steps[1].status == "not_started"


async def test_cancel_plan_deletes_task(monkeypatch):
    task = make_task()
    store = patch_store(monkeypatch, task)
    service = make_service(["should not be used"])

    outbound = await service.handle(message("cancel"))

    assert outbound.content == "已取消当前计划。"
    assert store["deleted"] is True


async def test_finishing_last_step_deletes_planning_task(monkeypatch):
    task = make_task(step_count=2)
    task.plan.steps[0].status = "completed"
    store = patch_store(monkeypatch, task)
    service = make_service(["last step result"])

    outbound = await service.handle(message("next"))

    assert "last step result" in outbound.content
    assert "计划已完成" in outbound.content
    assert store["deleted"] is True
    assert store["task"] is None
