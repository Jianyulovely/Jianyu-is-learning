"""
SQLite 数据模型与初始化
表：users, conversations, memories, scheduler_tasks
"""
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "companion.db"

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    nickname    TEXT,
    role_id     TEXT    NOT NULL DEFAULT 'jiejie',
    created_at  REAL    NOT NULL DEFAULT (unixepoch()),
    last_active_at REAL NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    role        TEXT    NOT NULL,   -- 'user' or 'assistant'
    content     TEXT    NOT NULL,
    emotion_tag TEXT,
    created_at  REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    content     TEXT    NOT NULL,
    importance  INTEGER NOT NULL DEFAULT 1,
    created_at  REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS scheduler_tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    task_type   TEXT    NOT NULL,
    trigger_at  REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending'
);
"""


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    return await aiosqlite.connect(DB_PATH)
