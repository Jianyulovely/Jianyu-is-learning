from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

PlanStepStatus = Literal["not_started", "in_progress", "completed", "blocked"]


class PlanStep(BaseModel):
    text: str
    status: PlanStepStatus = "not_started"
    notes: str = ""
    result_summary: str = ""


class PlanState(BaseModel):
    plan_id: str
    title: str
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: str
    updated_at: str

    def next_active_step_index(self) -> int | None:
        for index, step in enumerate(self.steps):
            if step.status in {"not_started", "in_progress"}:
                return index
        return None

    def completed_count(self) -> int:
        return sum(1 for step in self.steps if step.status == "completed")

    def total_count(self) -> int:
        return len(self.steps)

    def progress_ratio(self) -> float:
        total = self.total_count()
        return self.completed_count() / total if total else 0.0

    def with_step(self, index: int, **updates: Any) -> "PlanState":
        steps = [step.model_copy() for step in self.steps]
        if index < 0 or index >= len(steps):
            raise IndexError(f"step index out of range: {index}")
        current = steps[index].model_copy(update=updates)
        steps[index] = current
        return self.model_copy(update={"steps": steps})


def _normalize_steps(steps: list[str] | list[PlanStep]) -> list[PlanStep]:
    normalized: list[PlanStep] = []
    for step in steps:
        if isinstance(step, PlanStep):
            normalized.append(step)
        else:
            normalized.append(PlanStep(text=str(step)))
    return normalized


def create_plan_state(
    *,
    plan_id: str,
    title: str,
    steps: list[str] | list[PlanStep],
    created_at: str,
    updated_at: str,
) -> PlanState:
    return PlanState(
        plan_id=plan_id,
        title=title,
        steps=_normalize_steps(steps),
        created_at=created_at,
        updated_at=updated_at,
    )


def update_plan_state(
    plan: PlanState,
    *,
    title: str | None = None,
    steps: list[str] | list[PlanStep] | None = None,
    updated_at: str | None = None,
) -> PlanState:
    updates: dict[str, Any] = {}
    if title:
        updates["title"] = title
    if steps is not None:
        updates["steps"] = _normalize_steps(steps)
    if updated_at:
        updates["updated_at"] = updated_at
    else:
        updates["updated_at"] = datetime.utcnow().isoformat()
    return plan.model_copy(update=updates)


def mark_plan_step(
    plan: PlanState,
    *,
    step_index: int,
    step_status: PlanStepStatus,
    step_notes: str | None = None,
    result_summary: str | None = None,
    updated_at: str | None = None,
) -> PlanState:
    if step_index < 0 or step_index >= len(plan.steps):
        raise IndexError(f"step index out of range: {step_index}")

    steps = [step.model_copy() for step in plan.steps]
    current = steps[step_index].model_copy(update={"status": step_status})
    if step_notes is not None:
        current.notes = step_notes
    if result_summary is not None:
        current.result_summary = result_summary
    steps[step_index] = current
    return plan.model_copy(
        update={
            "steps": steps,
            "updated_at": updated_at or datetime.utcnow().isoformat(),
        }
    )
