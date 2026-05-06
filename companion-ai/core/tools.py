"""
工具定义与执行层。
- _TOOL_REGISTRY: 工具名 → schema 的字典
- TOOL_DEFINITIONS: 全量列表（供 fallback 或调试）
- select_tools: 小模型预选，返回本次需要的 schema 子集
- execute_tool: 根据工具名分发到具体实现，统一返回字符串供模型消费
"""
import json
import logging

from config import config
from core.http_client import safe_post

logger = logging.getLogger(__name__)

# ── 工具注册表 ────────────────────────────────────────────────────────────────

_TOOL_REGISTRY: dict[str, dict] = {
    "web_search": {
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
    },
    "search_documents": {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search the local research paper library for relevant content. "
                "Use this when the user asks about topics likely covered in academic papers, "
                "such as LLM architectures, training methods, attention mechanisms, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query describing what to look for.",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Optional paper collection name to search within. Omit to search all collections.",
                    },
                },
                "required": ["query"],
            },
        },
    },
}

TOOL_DEFINITIONS = list(_TOOL_REGISTRY.values())

# ── 小模型预选 ────────────────────────────────────────────────────────────────

_SELECT_SYSTEM = (
    "You select which tools are needed to answer a user message.\n"
    "Available tools:\n"
    "- web_search: current events, news, real-time info, prices, weather, anything recent\n"
    "- search_documents: academic papers, LLM architectures, training methods, research\n"
    "Pure conversation or personal questions need no tools.\n"
    'Output ONLY valid JSON, e.g. {"tools": ["web_search"]} or {"tools": []}'
)


async def select_tools(user_message: str) -> list[dict]:
    """小模型预选工具，出错时 fallback 到空列表（纯聊天模式）。"""
    payload = {
        "model": config.TOOL_SELECT_MODEL,
        "system": _SELECT_SYSTEM,
        "prompt": user_message,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }
    try:
        resp = await safe_post(
            config.OLLAMA_GEN_URL, json=payload, timeout=config.TOOL_SELECT_TIMEOUT
        )
        resp.raise_for_status()
        names: list[str] = json.loads(resp.json()["response"]).get("tools", [])
        selected = [_TOOL_REGISTRY[n] for n in names if n in _TOOL_REGISTRY]
        logger.info(f"[tool_select] tools={[n for n in names if n in _TOOL_REGISTRY]}")
        return selected
    except Exception as e:
        logger.warning(f"[tool_select] failed ({e}), using no tools")
        return []

# ── 工具执行入口 ──────────────────────────────────────────────────────────────

async def execute_tool(name: str, arguments: dict) -> str:
    """分发工具调用，返回字符串结果（成功或错误信息）。"""
    try:
        if name == "web_search":
            from search.tavily_search import tavily_search
            return await tavily_search(arguments.get("query", ""))
        if name == "search_documents":
            from rag.retriever import search
            return await search(
                query=arguments.get("query", ""),
                collection_name=arguments.get("collection"),
            )
        return f"[tool error] Unknown tool: {name}"
    except Exception as e:
        logger.error(f"Tool '{name}' failed: {e}")
        return f"[tool error] {name} failed: {str(e)}"

