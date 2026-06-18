from __future__ import annotations

import logging

import aiosqlite

from core.session.keys import history_key, image_desc_key, state_key
from db.models import DB_PATH
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


async def clear_history(user_id: int) -> None:
    """Erase conversation history without touching state (intimacy etc.).

    AUDIT B-04: previous implementation wiped the entire state hash, including
    intimacy_level, on /reset. Keep intimacy alive across resets.
    """
    try:
        r = get_redis()
        await r.delete(history_key(user_id))
        await r.delete(image_desc_key(user_id))
    except Exception as exc:
        logger.warning("clear_history redis failed user_id=%s: %s", user_id, exc)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM conversations WHERE user_id=?", (user_id,))
            await db.commit()
    except Exception as e:
        logger.warning("clear_history db failed: %s", e)


async def reset_all(user_id: int) -> None:
    """Hard reset: history + state + cached image desc.

    Use this only for explicit data-purge commands; ``clear_history`` is the
    everyday `/reset` path.
    """
    try:
        r = get_redis()
        await r.delete(history_key(user_id))
        await r.delete(state_key(user_id))
        await r.delete(image_desc_key(user_id))
    except Exception as exc:
        logger.warning("reset_all redis failed user_id=%s: %s", user_id, exc)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM conversations WHERE user_id=?", (user_id,))
            await db.commit()
    except Exception as e:
        logger.warning("reset_all db failed: %s", e)
