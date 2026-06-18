from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import yaml

from config import config
from core.agent.formatter import format_reply
from core.llm.client import LLMResult
from core.agent.state import AgentTaskState

logger = logging.getLogger(__name__)

# Tool 输出回灌 LLM 时的整体长度上限。Tavily 多结果 + 截断后仍可能超长，统一兜底。
MAX_OBSERVATION_CHARS = 4000
OBSERVATION_HEAD_CHARS = 2500
OBSERVATION_TAIL_CHARS = 1500


class ToolArgumentError(Exception):
    """Raised by parse_tool_arguments when the LLM emits unparseable arguments."""


def append_assistant_result(task: AgentTaskState, result: LLMResult) -> None:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": result.reply or "",
    }
    if result.tool_calls:
        message["tool_calls"] = result.tool_calls
    task.messages.append(message)


def tool_message(*, tool_call_id: str, name: str, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": content,
    }


def parse_tool_arguments(raw: Any) -> dict[str, Any]:
    """Parse a tool_call.function.arguments payload.

    Returns:
        dict of parsed kwargs, suitable for ``**arguments`` into a tool.
    Raises:
        ToolArgumentError: when payload cannot be coerced into a kwargs dict. Caller
        should turn this into a tool_message error string instead of calling the tool
        with invalid kwargs (AUDIT T-05).
    """
    if isinstance(raw, dict):
        return raw
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ToolArgumentError(f"arguments are not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ToolArgumentError(
            f"arguments must decode to an object, got {type(parsed).__name__}"
        )
    return parsed


def _truncate_observation(text: str) -> str:
    if len(text) <= MAX_OBSERVATION_CHARS:
        return text
    omitted = len(text) - OBSERVATION_HEAD_CHARS - OBSERVATION_TAIL_CHARS
    return (
        f"{text[:OBSERVATION_HEAD_CHARS]}"
        f"\n... observation truncated, {omitted} characters omitted ...\n"
        f"{text[-OBSERVATION_TAIL_CHARS:]}"
    )


def format_tool_result(result: Any) -> str:
    error = getattr(result, "error", None)
    if error:
        return _truncate_observation(f"[tool error] {error}")
    output = getattr(result, "output", result)
    text = str(output or "")
    return _truncate_observation(text)


def normalize_history(history: list[dict]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages


def first_user_message(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return ""


def append_agent_instructions(system_prompt: str) -> str:
    return (
        system_prompt
        + "\n\n"
        + "Agent instructions:\n"
        + "- You are a task-oriented agent, not only a chat assistant.\n"
        + "- Understand the user's goal first, then decide whether a tool is needed.\n"
        + "- Use tavily_search for current or external factual information.\n"
        + "- Use ask_human only when critical information is missing and cannot be inferred safely.\n"
        + "- Use computer_shell for local computer command-line tasks when needed.\n"
        + "- When the user says desktop, resolve it with PowerShell [Environment]::GetFolderPath('Desktop'); do not guess a path.\n"
        + "- After creating or writing a file with computer_shell, verify it with read-only commands such as Test-Path and Get-Content before saying it is done.\n"
        + "- Use terminate when the task is complete or cannot proceed further.\n"
        + "- Do not fabricate tool results.\n"
        + "- Do not expose internal JSON, tool calls, or implementation details to the user.\n"
        + "- For simple conversation, answer directly without forcing tool usage."
    )


def post_process(reply: str, role: dict[str, Any]) -> str:
    for phrase in role.get("forbidden_phrases", []):
        if phrase and phrase in reply:
            logger.warning("Forbidden phrase detected, using fallback.")
            return "我换一种更自然的说法继续和你聊。"
    return reply


def format_final_reply(reply: str, role: dict[str, Any]) -> str:
    reply = post_process(reply or "", role)
    reply = format_reply(reply)
    if not reply.strip():
        return "我刚才没组织好这句话，你再说一句，我接着陪你聊。"
    return reply


def load_role(role_id: str) -> dict:
    path = config.ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_role_for_user(db_user: dict | None, username: str) -> dict[str, Any]:
    role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
    return {
        "role_id": role_id,
        "user_name": (db_user or {}).get("nickname") or username or "用户",
        "username": username,
        "config": load_role(role_id),
    }


def coerce_user_id(value: str) -> int:
    """Coerce a sender id into a stable int.

    Numeric ids pass through. Non-numeric ids are mapped via SHA-1 so the result
    survives Python's randomized ``hash()`` (AUDIT B-02). Stable across restarts.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()
        # 取前 12 个十六进制位 → 48 bit，仍在 SQLite INTEGER 范围内
        return int(digest[:12], 16)
