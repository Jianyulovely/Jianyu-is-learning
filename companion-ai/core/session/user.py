from __future__ import annotations

import logging
from typing import Optional

import aiosqlite

from db.models import DB_PATH

logger = logging.getLogger(__name__)


async def ensure_user(user_id: int, username: str = "", role_id: str = "Alex") -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, role_id) VALUES (?,?,?)",
                (user_id, username, role_id),
            )
            await db.commit()
    except Exception as e:
        logger.warning("ensure_user failed: %s", e)


async def get_user(user_id: int) -> Optional[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.warning("get_user failed: %s", e)
        return None


async def set_role(user_id: int, role_id: str) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET role_id=? WHERE user_id=?", (role_id, user_id))
            await db.commit()
    except Exception as e:
        logger.warning("set_role failed: %s", e)


async def set_nickname(user_id: int, nickname: str) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET nickname=? WHERE user_id=?", (nickname, user_id))
            await db.commit()
    except Exception as e:
        logger.warning("set_nickname failed: %s", e)
