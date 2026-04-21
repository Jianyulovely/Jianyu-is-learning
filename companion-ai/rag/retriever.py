"""
RAG 检索模块。
query embedding 使用异步 httpx，直接传向量给 ChromaDB（不走同步 EmbeddingFunction）。
"""
import logging

import httpx

from config import config
from core.http_client import safe_post
from rag.chroma_client import get_collection

logger = logging.getLogger(__name__)


async def _get_embedding(text: str) -> list[float]:
    resp = await safe_post(
        config.OLLAMA_EMBED_URL,
        json={"model": config.EMBED_MODEL, "input": [text]},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


async def search(query: str, collection_name: str | None = None) -> str:
    """检索相关段落，返回格式化字符串供模型消费。"""
    try:
        collection = get_collection()
        if collection.count() == 0:
            return "[rag] 文档库为空，尚未索引任何论文。"

        embedding = await _get_embedding(query)

        kwargs: dict = {
            "query_embeddings": [embedding],
            "n_results": min(config.RAG_TOP_K, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if collection_name:
            kwargs["where"] = {"collection": collection_name}

        results = collection.query(**kwargs)
        return _format_results(results)

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return f"[rag error] Search failed: {e}"


def _format_results(results: dict) -> str:
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return "[rag] No relevant content found."

    top_n = config.RAG_EVIDENCE_TOP_N
    snippet_len = config.RAG_SNIPPET_LEN
    BADGES = ["①", "②", "③", "④", "⑤"]

    parts = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        if i >= top_n:
            break
        source = meta.get("source", "unknown")
        page = meta.get("page", "?")
        score = round(1 - dist, 3)   # cosine distance → similarity
        snippet = doc[:snippet_len].rstrip()
        if len(doc) > snippet_len:
            snippet += "…"
        badge = BADGES[i] if i < len(BADGES) else f"[{i+1}]"
        parts.append(f"{badge} [{source} · p.{page} · 相似度 {score}]\n{snippet}")

    return "\n\n".join(parts)
