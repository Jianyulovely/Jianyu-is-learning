from __future__ import annotations

import logging

import aiosqlite

from config import config
from core.session.keys import image_desc_key
from db.models import DB_PATH
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


async def get_last_image_desc(user_id: int) -> str:
    r = get_redis()
    raw = await r.get(image_desc_key(user_id))
    return raw if isinstance(raw, str) else (raw.decode() if raw else "")


async def set_last_image_desc(user_id: int, desc: str) -> None:
    r = get_redis()
    await r.set(image_desc_key(user_id), desc, ex=config.SESSION_TTL)


async def save_image_memory(user_id: int, desc: str) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO memories (user_id, content, importance) VALUES (?,?,?)",
                (user_id, f"[图片] {desc}", 2),
            )
            await db.commit()
    except Exception as e:
        logger.warning("save_image_memory failed: %s", e)
