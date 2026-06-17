from __future__ import annotations

import logging

import aiosqlite

from config import config
from core.session.keys import state_key
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


async def get_state(user_id: int) -> dict:
    r = get_redis()
    state = await r.hgetall(state_key(user_id))
    if not state:
        return {"emotion_tag": "neutral", "intimacy_level": str(config.INTIMACY_INIT)}
    return state


async def update_state(user_id: int, **kwargs) -> None:
    r = get_redis()
    key = state_key(user_id)
    await r.hset(key, mapping={k: str(v) for k, v in kwargs.items()})
    await r.expire(key, config.SESSION_TTL)


async def get_intimacy(user_id: int) -> int:
    state = await get_state(user_id)
    return int(state.get("intimacy_level", config.INTIMACY_INIT))


async def bump_intimacy(user_id: int, emotion_tag: str) -> None:
    delta = {"romantic": 5, "happy": 2, "sad": 1, "stressed": 1, "neutral": 0}
    inc = delta.get(emotion_tag, 0)
    if inc == 0:
        return
    current = await get_intimacy(user_id)
    new_val = min(100, current + inc)
    await update_state(user_id, intimacy_level=new_val)
