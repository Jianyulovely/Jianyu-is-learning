from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["running", "waiting_human", "done", "failed"]


class AgentTaskState(BaseModel):
    status: TaskStatus
    messages: list[dict[str, Any]] = Field(default_factory=list)
    pending_tool_call_id: str | None = None
    pending_tool_name: str | None = None
    pending_question: str | None = None
    started_at: str
    updated_at: str
