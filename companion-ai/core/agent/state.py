from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from core.planning.models import PlanState

TaskStatus = Literal["running", "waiting_human", "done", "failed"]
TaskMode = Literal["chat", "planning"]


class AgentTaskState(BaseModel):
    status: TaskStatus
    mode: TaskMode = "chat"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    plan: PlanState | None = None
    current_step_index: int | None = None
    pending_tool_call_id: str | None = None
    pending_tool_name: str | None = None
    pending_question: str | None = None
    pending_shell_command: str | None = None
    pending_shell_cwd: str | None = None
    pending_shell_reason: str | None = None
    # 一次性 shell 审批凭证：approved_for_call_id 标识哪个 tool_call_id 被授权。
    # 进入工具调用前立刻置 None，避免被复用。
    approved_for_call_id: str | None = None
    # 保留原字段做向后兼容（旧 Redis 数据反序列化时不报错），但新代码不再写入。
    approved_shell_command: str | None = None
    approved_shell_cwd: str | None = None
    # 缓存进入任务时的初始情绪标签，避免 waiting_human resume 时用确认短语重判。
    initial_emotion_tag: str | None = None
    started_at: str
    updated_at: str
