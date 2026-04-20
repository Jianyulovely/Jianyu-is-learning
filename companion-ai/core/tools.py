"""
工具定义与执行层。
- TOOL_DEFINITIONS: 传给模型的 JSON schema 列表
- execute_tool: 根据工具名分发到具体实现，统一返回字符串供模型消费
"""
import logging

import httpx

from config import config

logger = logging.getLogger(__name__)

# ── 工具定义（传给 Ollama 的 schema） ────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for real-time or up-to-date information. "
                "Use this when the user asks about current events, news, weather, "
                "prices, or anything that may have changed recently."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in the most effective form.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# ── 工具执行入口 ──────────────────────────────────────────────────────────────

async def execute_tool(name: str, arguments: dict) -> str:
    """分发工具调用，返回字符串结果（成功或错误信息）。"""
    try:
        if name == "web_search":
            return await _tavily_search(arguments.get("query", ""))
        return f"[tool error] Unknown tool: {name}"
    except Exception as e:
        logger.error(f"Tool '{name}' failed: {e}")
        return f"[tool error] {name} failed: {str(e)}"

# ── Tavily 搜索实现 ───────────────────────────────────────────────────────────

async def _tavily_search(query: str) -> str:
    if not query:
        return "[tool error] Empty search query."
    if not config.TAVILY_API_KEY:
        return "[tool error] TAVILY_API_KEY not configured."

    logger.info(f"[Tavily] query: {query!r}")

    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 5,
        "include_answer": True,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        data = resp.json()

    return _format_tavily_results(data)


def _format_tavily_results(data: dict) -> str:
    parts = []

    answer = data.get("answer", "")
    if answer:
        parts.append(f"Summary: {answer}")

    results = data.get("results", [])
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")[:300]
        parts.append(f"[{i}] {title}\n{url}\n{content}")

    if not parts:
        return "[tool error] No results found."

    return "\n\n".join(parts)
