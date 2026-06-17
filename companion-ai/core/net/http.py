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
            logger.warning("POST %s attempt %s failed: %s, retrying...", url, attempt + 1, e)


async def safe_get(url: str, *, retries: int = 3, **kwargs) -> httpx.Response:
    client = get_client()
    for attempt in range(retries):
        try:
            return await client.get(url, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            logger.warning("GET %s attempt %s failed: %s, retrying...", url, attempt + 1, e)
