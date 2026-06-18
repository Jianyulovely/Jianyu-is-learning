from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.models import RequestPayload
from config import config
from core.planning.formatter import format_plan_text, format_step_update
from core.planning.models import (
    PlanState,
    create_plan_state,
    mark_plan_step,
)
from core.tool.planning import PlanningTool

logger = logging.getLogger(__name__)


@dataclass
class PlanningDecision:
    needs_plan: bool
    title: str
    steps: list[str]
    rationale: str = ""


class PlanningFlow:
    def __init__(self, llm_client) -> None:
        self._llm_client = llm_client
        self._planning_tool = PlanningTool()

    async def decide(
        self,
        *,
        user_message: str,
        images: list[str] | None = None,
    ) -> PlanningDecision:
        images = images or []
        if not self._looks_complex(user_message, images):
            return PlanningDecision(needs_plan=False, title="", steps=[])

        system_prompt = (
            "You are a planning router. Decide whether the request needs an explicit "
            "multi-step plan. Return JSON with keys: needs_plan, title, steps, rationale. "
            "If needs_plan is false, steps must be an empty list. "
            "If needs_plan is true, return 3 to 7 concise executable steps. "
            "Steps must be concrete actions the agent can perform with its tools "
            "(read files, run shell commands, search the web). Do NOT include manual "
            "actions like 'open an IDE' or 'use a text editor' — the agent has no GUI. "
            "Optionally prefix a step with [SHELL] or [SEARCH] to hint the executor "
            "type; omit the marker for default agent handling."
        )
        request = (
            "Analyze this user request and decide if a plan is needed.\n"
            f"Request: {user_message}\n"
            f"Has images: {bool(images)}"
        )
        try:
            result = await self._llm_client.chat(
                RequestPayload(
                    system_prompt=system_prompt,
                    history_messages=[{"role": "user", "content": request}],
                    response_format={"type": "json_object"},
                )
            )
            payload = self._parse_json(result.reply)
            if isinstance(payload, dict):
                needs_plan = bool(payload.get("needs_plan"))
                title = str(payload.get("title") or "Complex task plan")
                steps = [str(step).strip() for step in payload.get("steps") or [] if str(step).strip()]
                rationale = str(payload.get("rationale") or "")
                if needs_plan and steps:
                    return PlanningDecision(
                        needs_plan=True,
                        title=title,
                        steps=steps[:7],
                        rationale=rationale,
                    )
        except Exception as exc:
            logger.warning("planning decision failed, falling back to heuristic: %s", exc)

        if self._looks_complex(user_message, images):
            return PlanningDecision(
                needs_plan=True,
                title=self._default_title(user_message),
                steps=self._default_steps(user_message, images),
            )
        return PlanningDecision(needs_plan=False, title="", steps=[])

    async def create_plan(
        self,
        *,
        plan_id: str,
        user_message: str,
        current_time_iso: str,
        timezone_name: str,
        decision: PlanningDecision,
    ) -> PlanState:
        return create_plan_state(
            plan_id=plan_id,
            title=decision.title,
            steps=decision.steps,
            created_at=current_time_iso,
            updated_at=current_time_iso,
        )

    def render_plan(self, plan: PlanState, *, current_step_index: int | None = None) -> str:
        return format_plan_text(plan, current_step_index=current_step_index)

    def mark_step_started(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="in_progress",
            updated_at=updated_at,
        )

    def mark_step_completed(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
        note: str = "",
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="completed",
            step_notes=note or None,
            updated_at=updated_at,
        )

    def mark_step_blocked(
        self,
        plan: PlanState,
        *,
        step_index: int,
        updated_at: str,
        note: str = "",
    ) -> PlanState:
        return mark_plan_step(
            plan,
            step_index=step_index,
            step_status="blocked",
            step_notes=note or None,
            updated_at=updated_at,
        )

    def build_step_system_prompt(
        self,
        *,
        base_prompt: str,
        plan: PlanState,
        step_index: int,
    ) -> str:
        step = plan.steps[step_index]
        return (
            base_prompt
            + "\n\nYou are executing a structured plan.\n"
            + "Only work on the current step below.\n"
            + "Do not skip ahead.\n"
            + "If the step requires local computer work, use computer_shell as needed.\n"
            + "If you create or modify files, verify the result with read-only tools before finishing the step.\n"
            + "If you need the user to clarify something, use ask_human.\n"
            + "If the whole plan cannot proceed at all (missing prerequisites, "
              "permission denied, irrecoverable error), call terminate(status='failure') "
              "to abort the entire plan instead of carrying on.\n"
            + "If the step is done, return a concise outcome.\n\n"
            + f"Current plan:\n{self.render_plan(plan, current_step_index=step_index)}\n\n"
            + f"Current step:\n{step_index + 1}. {step.text}\n"
        )

    def format_step_progress(
        self,
        plan: PlanState,
        *,
        step_index: int,
        prefix: str = "Progress: ",
    ) -> str:
        return format_step_update(plan, step_index=step_index, prefix=prefix)

    def _default_title(self, user_message: str) -> str:
        text = user_message.strip()
        if len(text) > 20:
            return f"Plan for: {text[:20]}"
        return f"Plan for: {text}"

    def _default_steps(self, user_message: str, images: list[str]) -> list[str]:
        steps = ["Clarify the task goal", "Execute the main actions", "Verify the result"]
        if images:
            steps.insert(1, "Analyze the provided image(s)")
        if any(keyword in user_message.lower() for keyword in ["电脑", "浏览", "打开", "点击", "安装", "运行"]):
            steps.append("Perform the required computer-side operation")
        return steps[:7]

    def _looks_complex(self, user_message: str, images: list[str]) -> bool:
        text = user_message.strip()
        keywords = [
            "整理",
            "比较",
            "规划",
            "计划",
            "执行",
            "完成",
            "电脑",
            "浏览",
            "打开",
            "点击",
            "安装",
            "下载",
            "写一个",
            "帮我做",
            "帮我完成",
            "多步骤",
            "总结",
            "分析",
            "研究",
        ]
        if images:
            return True
        if len(text) >= 40:
            return True
        return any(keyword in text for keyword in keywords)

    def _parse_json(self, raw: str):
        try:
            return json.loads(raw)
        except Exception:
            return None
