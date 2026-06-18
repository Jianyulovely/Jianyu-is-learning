from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.session import cleanup, history, image, state


class BrokenRedis:
    async def get(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def set(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def hgetall(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def hset(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def expire(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")

    async def delete(self, *args, **kwargs):
        raise ConnectionError("redis unavailable")


@pytest.fixture
def broken_redis(monkeypatch):
    redis = BrokenRedis()
    monkeypatch.setattr(history, "get_redis", lambda: redis)
    monkeypatch.setattr(state, "get_redis", lambda: redis)
    monkeypatch.setattr(image, "get_redis", lambda: redis)
    monkeypatch.setattr(cleanup, "get_redis", lambda: redis)
    return redis


async def test_get_history_falls_back_to_sql_when_redis_fails(monkeypatch, broken_redis):
    async def fake_load_history_from_db(user_id: int):
        assert user_id == 42
        return [{"role": "user", "content": "from sqlite"}]

    monkeypatch.setattr(history, "load_history_from_db", fake_load_history_from_db)

    assert await history.get_history(42) == [{"role": "user", "content": "from sqlite"}]


async def test_append_message_persists_to_sql_when_redis_fails(monkeypatch, broken_redis):
    persisted = []

    async def fake_load_history_from_db(user_id: int):
        assert user_id == 42
        return [{"role": "user", "content": "old"}]

    async def fake_persist_message(user_id: int, role: str, content: str):
        persisted.append((user_id, role, content))

    monkeypatch.setattr(history, "load_history_from_db", fake_load_history_from_db)
    monkeypatch.setattr(history, "persist_message", fake_persist_message)

    await history.append_message(42, "assistant", "new")

    assert persisted == [(42, "assistant", "new")]


async def test_state_and_image_cache_ignore_redis_failure(broken_redis):
    assert await state.get_state(42) == {"emotion_tag": "neutral", "intimacy_level": "20"}
    await state.update_state(42, emotion_tag="happy")
    assert await image.get_last_image_desc(42) == ""
    await image.set_last_image_desc(42, "desc")


async def test_clear_history_still_deletes_sql_when_redis_fails(monkeypatch, broken_redis):
    deleted = []

    class FakeCursor:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeDb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, sql, params):
            deleted.append((sql, params))
            return FakeCursor()

        async def commit(self):
            deleted.append(("commit", ()))

    monkeypatch.setattr(cleanup.aiosqlite, "connect", lambda path: FakeDb())

    await cleanup.clear_history(42)

    assert deleted == [
        ("DELETE FROM conversations WHERE user_id=?", (42,)),
        ("commit", ()),
    ]
