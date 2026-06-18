from __future__ import annotations

from typing import Any, Literal

from core.planning.formatter import format_plan_text
from core.planning.models import (
    PlanState,
    PlanStep,
    PlanStepStatus,
    create_plan_state,
    mark_plan_step,
    update_plan_state,
)
from core.tool.base import BaseTool, ToolError, ToolResult


_PLANNING_DESCRIPTION_FULL = (
    "Create and update structured plans for complex tasks. "
    "Use it to manage plan steps, step statuses, and progress tracking."
)
_PLANNING_DESCRIPTION_EXECUTE = (
    "Inspect or update step status for the currently active plan. "
    "Use 'get' to view progress, 'mark_step' to move a step between "
    "not_started/in_progress/completed/blocked. Creating or restructuring the plan "
    "is not allowed during step execution."
)


def _parameters_for(stage: str) -> dict:
    """Return JSON schema scoped to the agent stage.

    stage='create' exposes the full command set used when the planner first builds
    a plan; stage='execute' only exposes read/mark_step so the worker agent cannot
    blow away the plan mid-execution (AUDIT T-11).
    """
    if stage == "execute":
        commands = ["get", "mark_step"]
    else:
        commands = ["create", "update", "get", "mark_step"]
    return {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": commands,
                "description": "Plan command.",
            },
            "plan_id": {
                "type": "string",
                "description": "Plan identifier.",
            },
            "title": {
                "type": "string",
                "description": "Plan title.",
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered plan steps.",
            },
            "step_index": {
                "type": "integer",
                "description": "0-based step index.",
            },
            "step_status": {
                "type": "string",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "description": "Step status.",
            },
            "step_notes": {
                "type": "string",
                "description": "Optional step notes.",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }


class PlanningTool(BaseTool):
    name: str = "planning"
    description: str = _PLANNING_DESCRIPTION_FULL
    parameters: dict = _parameters_for("create")
    # 区分 agent 处于哪个阶段：create / execute
    stage: Literal["create", "execute"] = "create"

    def __init__(self, *, stage: Literal["create", "execute"] = "create", **data: Any) -> None:
        super().__init__(stage=stage, **data)
        self.parameters = _parameters_for(stage)
        self.description = (
            _PLANNING_DESCRIPTION_FULL
            if stage == "create"
            else _PLANNING_DESCRIPTION_EXECUTE
        )

    async def execute(
        self,
        *,
        command: Literal["create", "update", "get", "mark_step"],
        plan_id: str | None = None,
        title: str | None = None,
        steps: list[str] | None = None,
        step_index: int | None = None,
        step_status: PlanStepStatus | None = None,
        step_notes: str | None = None,
        plan: PlanState | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        **_: Any,
    ) -> ToolResult:
        if self.stage == "execute" and command in {"create", "update"}:
            raise ToolError(
                f"Command '{command}' is not allowed during step execution. "
                "Use 'get' or 'mark_step' only."
            )

        if command == "create":
            if not plan_id:
                raise ToolError("plan_id is required for create")
            if not title:
                raise ToolError("title is required for create")
            if not steps:
                raise ToolError("steps are required for create")
            if not created_at or not updated_at:
                raise ToolError("created_at and updated_at are required for create")
            plan = create_plan_state(
                plan_id=plan_id,
                title=title,
                steps=steps,
                created_at=created_at,
                updated_at=updated_at,
            )
            return self.success_response(format_plan_text(plan))

        if command == "update":
            if not plan:
                raise ToolError("plan is required for update")
            plan = update_plan_state(
                plan,
                title=title,
                steps=steps,
                updated_at=updated_at,
            )
            return self.success_response(format_plan_text(plan))

        if command == "get":
            if not plan:
                raise ToolError("plan is required for get")
            return self.success_response(format_plan_text(plan))

        if command == "mark_step":
            if not plan:
                raise ToolError("plan is required for mark_step")
            if step_index is None:
                raise ToolError("step_index is required for mark_step")
            if not step_status:
                raise ToolError("step_status is required for mark_step")
            plan = mark_plan_step(
                plan,
                step_index=step_index,
                step_status=step_status,
                step_notes=step_notes,
                updated_at=updated_at,
            )
            return self.success_response(format_plan_text(plan, current_step_index=step_index))

        raise ToolError(f"Unsupported command: {command}")
