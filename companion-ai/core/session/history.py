from __future__ import annotations

import json
import logging

import aiosqlite

from config import config
from core.session.keys import history_key
from db.models import DB_PATH
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


async def get_history(user_id: int) -> list[dict]:
    r = get_redis()
    raw = await r.get(history_key(user_id))
    if raw:
        return json.loads(raw)
    return await load_history_from_db(user_id)


async def append_message(user_id: int, role: str, content: str) -> None:
    r = get_redis()
    key = history_key(user_id)
    history = await get_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > config.MAX_HISTORY_MSGS:
        history = history[-config.MAX_HISTORY_MSGS:]
    await r.set(key, json.dumps(history, ensure_ascii=False), ex=config.SESSION_TTL)
    await persist_message(user_id, role, content)


async def load_history_from_db(user_id: int) -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT role, content FROM conversations "
                "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, config.MAX_HISTORY_MSGS),
            ) as cur:
                rows = await cur.fetchall()
        msgs = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        if msgs:
            r = get_redis()
            await r.set(
                history_key(user_id),
                json.dumps(msgs, ensure_ascii=False),
                ex=config.SESSION_TTL,
            )
        return msgs
    except Exception as e:
        logger.warning("load_history_from_db failed: %s", e)
        return []


async def persist_message(user_id: int, role: str, content: str) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, role, content, emotion_tag) VALUES (?,?,?,?)",
                (user_id, role, content, None),
            )
            await db.execute(
                "UPDATE users SET last_active_at=unixepoch() WHERE user_id=?",
                (user_id,),
            )
            await db.commit()
    except Exception as e:
        logger.warning("persist_message failed: %s", e)
