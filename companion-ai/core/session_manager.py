"""
Session Manager —— Redis Hash 会话缓存 + SQLite 持久化
- session:{user_id}:history  → JSON list，最近 24 条消息，TTL=7200s
- session:{user_id}:state    → Hash，存储 emotion_tag / intimacy_level，TTL=7200s
"""
import json
import logging
from typing import Optional

import aiosqlite

from db.redis_client import get_redis
from db.models import DB_PATH

logger = logging.getLogger(__name__)

SESSION_TTL = 7200          # 2 小时
MAX_HISTORY_MSGS = 24       # 最近 12 轮 × 2
INTIMACY_INIT = 20


def _history_key(user_id: int) -> str:
    return f"session:{user_id}:history"


def _state_key(user_id: int) -> str:
    return f"session:{user_id}:state"


class SessionManager:

    # ── 历史记录 ──────────────────────────────────────────────────────────────

    async def get_history(self, user_id: int) -> list[dict]:
        r = get_redis()
        raw = await r.get(_history_key(user_id))
        if raw:
            return json.loads(raw)
        # Redis 中没有 → 从 SQLite 加载最近历史
        return await self._load_history_from_db(user_id)

    async def append_message(self, user_id: int, role: str, content: str, emotion_tag: str = "neutral"):
        r = get_redis()
        key = _history_key(user_id)

        history = await self.get_history(user_id)
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY_MSGS:
            history = history[-MAX_HISTORY_MSGS:]

        await r.set(key, json.dumps(history, ensure_ascii=False), ex=SESSION_TTL)

        # 同步写 SQLite
        await self._persist_message(user_id, role, content, emotion_tag)

    async def _load_history_from_db(self, user_id: int) -> list[dict]:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT role, content FROM conversations "
                    "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                    (user_id, MAX_HISTORY_MSGS),
                ) as cur:
                    rows = await cur.fetchall()
            msgs = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
            # 写回 Redis
            if msgs:
                r = get_redis()
                await r.set(
                    _history_key(user_id),
                    json.dumps(msgs, ensure_ascii=False),
                    ex=SESSION_TTL,
                )
            return msgs
        except Exception as e:
            logger.warning(f"load_history_from_db failed: {e}")
            return []

    async def _persist_message(self, user_id: int, role: str, content: str, emotion_tag: str):
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO conversations (user_id, role, content, emotion_tag) VALUES (?,?,?,?)",
                    (user_id, role, content, emotion_tag),
                )
                await db.execute(
                    "UPDATE users SET last_active_at=unixepoch() WHERE user_id=?",
                    (user_id,),
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"persist_message failed: {e}")

    # ── 状态（情绪 + 亲密度） ─────────────────────────────────────────────────

    async def get_state(self, user_id: int) -> dict:
        r = get_redis()
        state = await r.hgetall(_state_key(user_id))
        if not state:
            return {"emotion_tag": "neutral", "intimacy_level": str(INTIMACY_INIT)}
        return state

    async def update_state(self, user_id: int, **kwargs):
        r = get_redis()
        key = _state_key(user_id)
        await r.hset(key, mapping={k: str(v) for k, v in kwargs.items()})
        await r.expire(key, SESSION_TTL)

    async def get_intimacy(self, user_id: int) -> int:
        state = await self.get_state(user_id)
        return int(state.get("intimacy_level", INTIMACY_INIT))

    async def bump_intimacy(self, user_id: int, emotion_tag: str):
        """根据情绪信号小幅增加亲密度"""
        delta = {"romantic": 5, "happy": 2, "sad": 1, "stressed": 1, "neutral": 0}
        inc = delta.get(emotion_tag, 0)
        if inc == 0:
            return
        current = await self.get_intimacy(user_id)
        new_val = min(100, current + inc)
        await self.update_state(user_id, intimacy_level=new_val)

    # ── 用户注册 ──────────────────────────────────────────────────────────────

    async def ensure_user(self, user_id: int, username: str = "", role_id: str = "jiejie"):
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, role_id) VALUES (?,?,?)",
                    (user_id, username, role_id),
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"ensure_user failed: {e}")

    async def get_user(self, user_id: int) -> Optional[dict]:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM users WHERE user_id=?", (user_id,)
                ) as cur:
                    row = await cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"get_user failed: {e}")
            return None

    async def set_nickname(self, user_id: int, nickname: str):
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET nickname=? WHERE user_id=?", (nickname, user_id)
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"set_nickname failed: {e}")
