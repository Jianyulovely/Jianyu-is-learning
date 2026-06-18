from __future__ import annotations

import logging

import aiosqlite

from config import config
from core.session.keys import state_key
from db.redis_client import get_redis

logger = logging.getLogger(__name__)

# Atomic intimacy bump (AUDIT B-06): read-modify-write done server-side so concurrent
# messages from the same user can't lose increments.
_INTIMACY_BUMP_LUA = """
local current = tonumber(redis.call('HGET', KEYS[1], 'intimacy_level') or ARGV[2])
local new = math.min(100, current + tonumber(ARGV[1]))
redis.call('HSET', KEYS[1], 'intimacy_level', new)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
return new
"""


async def get_state(user_id: int) -> dict:
    try:
        state = await get_redis().hgetall(state_key(user_id))
    except Exception as exc:
        logger.warning("state redis get failed user_id=%s: %s", user_id, exc)
        state = {}
    if not state:
        return {"emotion_tag": "neutral", "intimacy_level": str(config.INTIMACY_INIT)}
    return state


async def update_state(user_id: int, **kwargs) -> None:
    try:
        r = get_redis()
        key = state_key(user_id)
        await r.hset(key, mapping={k: str(v) for k, v in kwargs.items()})
        await r.expire(key, config.SESSION_TTL)
    except Exception as exc:
        logger.warning("state redis set failed user_id=%s: %s", user_id, exc)


async def get_intimacy(user_id: int) -> int:
    state = await get_state(user_id)
    return int(state.get("intimacy_level", config.INTIMACY_INIT))


async def bump_intimacy(user_id: int, emotion_tag: str) -> None:
    delta = {"romantic": 5, "happy": 2, "sad": 1, "stressed": 1, "neutral": 0}
    inc = delta.get(emotion_tag, 0)
    if inc == 0:
        return
    try:
        r = get_redis()
        await r.eval(
            _INTIMACY_BUMP_LUA,
            1,
            state_key(user_id),
            inc,
            config.INTIMACY_INIT,
            config.SESSION_TTL,
        )
    except Exception as exc:
        # Lua not available? Fall back to read-modify-write (lossy under concurrency
        # but at least functional during dev).
        logger.warning("intimacy lua bump failed user_id=%s: %s", user_id, exc)
        current = await get_intimacy(user_id)
        new_val = min(100, current + inc)
        await update_state(user_id, intimacy_level=new_val)
