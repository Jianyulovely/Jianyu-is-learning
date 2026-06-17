from __future__ import annotations

import logging

import aiosqlite

from core.session.keys import history_key, image_desc_key, state_key
from db.models import DB_PATH
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


async def clear_history(user_id: int) -> None:
    r = get_redis()
    await r.delete(history_key(user_id))
    await r.delete(state_key(user_id))
    await r.delete(image_desc_key(user_id))
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM conversations WHERE user_id=?", (user_id,))
            await db.commit()
    except Exception as e:
        logger.warning("clear_history db failed: %s", e)
