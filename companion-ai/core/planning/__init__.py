from __future__ import annotations

import importlib
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.planning.flow import PlanningDecision, PlanningFlow
    from core.planning.formatter import format_plan_text, format_plan_title
    from core.planning.models import (
        PlanState,
        PlanStep,
        PlanStepStatus,
        create_plan_state,
        mark_plan_step,
        update_plan_state,
    )

__all__ = [
    "PlanState",
    "PlanStep",
    "PlanStepStatus",
    "PlanningDecision",
    "PlanningFlow",
    "create_plan_state",
    "format_plan_text",
    "format_plan_title",
    "mark_plan_step",
    "update_plan_state",
]


def __getattr__(name: str) -> Any:
    if name in {"PlanningDecision", "PlanningFlow"}:
        module = importlib.import_module("core.planning.flow")
        return getattr(module, name)
    if name in {"format_plan_text", "format_plan_title"}:
        module = importlib.import_module("core.planning.formatter")
        return getattr(module, name)
    if name in {
        "PlanState",
        "PlanStep",
        "PlanStepStatus",
        "create_plan_state",
        "mark_plan_step",
        "update_plan_state",
    }:
        module = importlib.import_module("core.planning.models")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
