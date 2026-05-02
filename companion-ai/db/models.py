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
    role_id     TEXT    NOT NULL DEFAULT 'Alex',
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

CREATE TABLE IF NOT EXISTS long_term_memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    memory_type     TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    keywords_json   TEXT    NOT NULL DEFAULT '[]',
    confidence      REAL    NOT NULL DEFAULT 0.8,
    source          TEXT    NOT NULL DEFAULT 'chat',
    status          TEXT    NOT NULL DEFAULT 'active',
    happened_at     REAL,
    created_at      REAL    NOT NULL DEFAULT (unixepoch()),
    updated_at      REAL    NOT NULL DEFAULT (unixepoch()),
    last_seen_at    REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_ltm_user_id
ON long_term_memories(user_id);

CREATE INDEX IF NOT EXISTS idx_ltm_user_type_status
ON long_term_memories(user_id, memory_type, status);

CREATE INDEX IF NOT EXISTS idx_ltm_user_updated
ON long_term_memories(user_id, updated_at DESC);

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
