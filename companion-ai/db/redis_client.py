"""
Redis 异步客户端封装
"""
import redis.asyncio as aioredis
import os

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _client = aioredis.from_url(url, decode_responses=True)
    return _client


async def close_redis():
    global _client
    if _client:
        await _client.aclose()
        _client = None
