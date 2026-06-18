from __future__ import annotations

from core.planning.models import PlanState


STATUS_MARKS = {
    "completed": "[x]",
    "in_progress": "[>]",
    "blocked": "[!]",
    "not_started": "[ ]",
}


def format_plan_title(plan: PlanState) -> str:
    total = plan.total_count()
    completed = plan.completed_count()
    return f"Plan: {plan.title} ({completed}/{total})"


def format_plan_text(plan: PlanState, *, current_step_index: int | None = None) -> str:
    lines = [
        f"Plan: {plan.title} (ID: {plan.plan_id})",
        f"Progress: {plan.completed_count()}/{plan.total_count()} steps completed",
        "Steps:",
    ]
    for index, step in enumerate(plan.steps):
        mark = STATUS_MARKS.get(step.status, STATUS_MARKS["not_started"])
        pointer = " ->" if current_step_index == index else ""
        lines.append(f"{index + 1}. {mark}{pointer} {step.text}")
        if step.notes:
            lines.append(f"   Notes: {step.notes}")
        if step.result_summary:
            lines.append(f"   Result: {step.result_summary}")
    return "\n".join(lines)


def format_step_update(
    plan: PlanState,
    *,
    step_index: int,
    prefix: str = "",
) -> str:
    if step_index < 0 or step_index >= len(plan.steps):
        return format_plan_text(plan)
    step = plan.steps[step_index]
    head = f"{prefix}{step.text}" if prefix else step.text
    return (
        f"{head}\n"
        f"Status: {step.status}\n"
        f"{format_plan_text(plan, current_step_index=step_index)}"
    )
