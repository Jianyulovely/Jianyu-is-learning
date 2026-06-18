from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from config import config
from core.agent.state import AgentTaskState
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


def task_session_key(channel: str, chat_id: str) -> str:
    return f"{channel}:{chat_id}"


def now_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).isoformat()


def _task_key(session_key: str) -> str:
    return f"agent_task:{session_key}"


async def load_task(session_key: str) -> AgentTaskState | None:
    try:
        raw = await get_redis().get(_task_key(session_key))
    except Exception as exc:
        logger.warning("load task from redis failed session_key=%s: %s", session_key, exc)
        return None
    if not raw:
        return None
    try:
        return AgentTaskState.model_validate_json(raw)
    except Exception:
        logger.warning("Invalid task state in Redis for session_key=%s", session_key)
        await delete_task(session_key)
        return None


async def save_task(session_key: str, task: AgentTaskState) -> None:
    try:
        await get_redis().set(
            _task_key(session_key),
            task.model_dump_json(),
            ex=config.SESSION_TTL,
        )
    except Exception as exc:
        logger.warning("save task to redis failed session_key=%s: %s", session_key, exc)


async def delete_task(session_key: str) -> None:
    try:
        await get_redis().delete(_task_key(session_key))
    except Exception as exc:
        logger.warning("delete task from redis failed session_key=%s: %s", session_key, exc)
