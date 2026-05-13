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

_SELECT_SYSTEM_PROMPT = """
You are a tool router.

Choose which tools are needed for answering the user query.

Available tools:

1. web_search
Use for:
- recent/current/latest information
- news
- weather
- stock prices
- sports results
- current APIs/models/releases
- websites/pages on the internet
- anything time-sensitive
- anything that may have changed recently

Examples:
- "latest OpenAI model"
- "weather in Tokyo"
- "today bitcoin price"
- "who won the NBA game"
- "search github repo"

2. search_documents
Use for:
- local knowledge base
- academic concepts
- technical explanations
- research papers
- LLM theory
- stored internal documents
- mathematical concepts
- programming knowledge
- long-form reference knowledge

Examples:
- "what is transformer architecture"
- "explain PPO"
- "what is RAG"
- "how does attention work"
- "summarize the paper"

Rules:
- If the query needs BOTH local knowledge AND current information, use both tools.
- If the query is casual conversation, output no tools.
- Prefer search_documents for stable knowledge.
- Prefer web_search for recent or changing information.

Output ONLY valid JSON.

Examples:
{"tools":["web_search"]}
{"tools":["search_documents"]}
{"tools":["web_search","search_documents"]}
{"tools":[]}
"""

async def select_tools(user_message: str) -> list[dict]:
    """小模型预选工具，出错时 fallback 到空列表（纯聊天模式）。"""
    payload = {
        "model": config.TOOL_SELECT_MODEL,
        "system": _SELECT_SYSTEM_PROMPT,
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

