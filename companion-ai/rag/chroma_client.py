"""
ChromaDB 客户端单例 + Ollama embedding 函数。
embedding 使用同步 requests（供 indexer 在 executor 里调用）。
"""
import logging
import re
import unicodedata

import requests
import chromadb
from chromadb import EmbeddingFunction, Embeddings

from config import config

logger = logging.getLogger(__name__)

_collection = None


def _clean(text: str) -> str:
    """去除 PDF 中常见的控制字符和 Unicode 私用区字符，保留可读内容。"""
    # 去除 ASCII 控制字符（保留 \t \n）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # 去除 Unicode 私用区（PDF 字体映射常用）
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    # NFKC 规范化（合字 ﬁ→fi 等）
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


class OllamaEmbeddingFunction(EmbeddingFunction):
    """调用本地 Ollama bge-m3 生成 embedding，逐条发送，过滤有问题的 chunk。"""

    MAX_CHARS = 2000

    def __call__(self, input: list[str]) -> Embeddings:
        embeddings = []
        for text in input:
            clean = _clean(text)[:self.MAX_CHARS]
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
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection 'papers' loaded, {_collection.count()} chunks.")
    return _collection
