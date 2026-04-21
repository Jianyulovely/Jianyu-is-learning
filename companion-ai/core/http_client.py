"""
全局共享的 httpx.AsyncClient 单例。
- 默认 timeout：connect=5s，read=120s，write=10s（适配本地 LLM 推理）
- 各调用方可在单次请求时用 timeout= 覆盖
- safe_post / safe_get：内置三次重试，网络抖动时自动恢复
"""
import logging

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def safe_post(url: str, *, retries: int = 3, **kwargs) -> httpx.Response:
    client = get_client()
    for attempt in range(retries):
        try:
            return await client.post(url, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            logger.warning(f"POST {url} attempt {attempt + 1} failed: {e}, retrying...")


async def safe_get(url: str, *, retries: int = 3, **kwargs) -> httpx.Response:
    client = get_client()
    for attempt in range(retries):
        try:
            return await client.get(url, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            logger.warning(f"GET {url} attempt {attempt + 1} failed: {e}, retrying...")
