"""
ChromaDB 客户端单例 + Ollama embedding 函数。
embedding 使用同步 requests（供 indexer 在 executor 里调用）。
"""
import logging

import requests
import chromadb
from chromadb import EmbeddingFunction, Embeddings

from rag.utils import _clean
from config import config

logger = logging.getLogger(__name__)

_collection = None


class OllamaEmbeddingFunction(EmbeddingFunction):
    """调用本地 Ollama bge-m3 生成 embedding，逐条发送，过滤有问题的 chunk。"""

    def __call__(self, input: list[str]) -> Embeddings:
        embeddings = []
        for text in input:
            clean = _clean(text)
            # 防止清理后为空字符串
            if not clean:
                embeddings.append([0.0] * 1024)
                continue
            try:
                resp = requests.post(
                    config.OLLAMA_EMBED_URL,
                    json={"model": config.EMBED_MODEL, "input": clean},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                vec = data.get("embeddings", [data.get("embedding")])[0]
                embeddings.append(vec)

            except Exception as e:
                logger.warning(f"Embedding failed (len={len(clean)}): {e}")
                embeddings.append([0.0] * 1024)

        return embeddings


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = client.get_or_create_collection(
            name="papers",
            embedding_function=OllamaEmbeddingFunction(),
            # 使用 HNSW 索引算法 + 余弦相似度进行向量检索
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection 'papers' loaded, {_collection.count()} chunks.")
    return _collection
