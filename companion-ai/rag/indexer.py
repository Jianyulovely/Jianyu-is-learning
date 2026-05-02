"""
PDF 扫描与增量索引。
- 扫描 docs/ 下所有子目录（每个子目录是一个论文集）
- 用 MD5 判断文件是否变更，只处理新增或修改的 PDF
- 用 pymupdf 提取段落级文字块，写入 ChromaDB
"""
import hashlib
import json
import logging
import re

from pathlib import Path

import fitz  # pymupdf

from config import config
from rag.chroma_client import get_collection
from rag.utils import _clean

logger = logging.getLogger(__name__)

HASH_FILE = config.CHROMA_DIR / "indexed_files.json"

OVERLAP_RATIO = 0.6
MIN_CHUNK_LEN = 50

CHUNK_SIZE = 768     # 文档块大小
OVERLAP_RATIO = 0.6   # 块重合比例
MIN_CHUNK_LEN = 50    # 过短的块（页眉/页脚/图注）直接丢弃

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _safe_id(text: str) -> str:
    """把任意字符串转成 ChromaDB 合法 ID（只保留字母数字和 _-）。"""
    return re.sub(r"[^\w\-]", "_", text)


def _extract_chunks(pdf_path: Path, collection_name: str) -> list[dict]:
    """用 pymupdf 提取段落级文字块，返回 chunk 列表。"""
    
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.warning(f"Cannot open {pdf_path.name}: {e}")
        return []

    doc_id = f"{collection_name}/{pdf_path.name}"

    full_text = ""
    offsets = []
    # step1: 拼接+记录来源
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)
        for block_idx, block in enumerate(blocks):
            if block[6] != 0:        # 跳过图片块
                continue
            text = block[4]
            text = _clean(text)
            
            if len(text) < MIN_CHUNK_LEN:    # 过滤页眉/页脚/短碎片
                continue
            if re.fullmatch(r"[\d\s\-–—]+", text):  # 跳过纯数字行（页码）
                continue
            
            start = len(full_text)
            full_text += text + "\n"
            end = len(full_text)
            
            offsets.append({
                "start": start,
                "end": end,
                "page": page_num,
                "block_id": block_idx                
            })
    doc.close()

    # step2: chunk化
    overlap = int(CHUNK_SIZE * OVERLAP_RATIO)
    overlap = int(CHUNK_SIZE * OVERLAP_RATIO)
    chunks = []
    start = 0
    text_len = len(full_text)

    while start < text_len:
        end = start + CHUNK_SIZE
        chunk_text = full_text[start:end]

        # Step 3: 找对应 metadata
        related = [ o for o in offsets if not (o["end"] < start or o["start"] > end) ]

        pages = list(set(o["page"] for o in related))

        chunks.append({
            "text": chunk_text.strip(),
            "metadata": {
                "doc_id": doc_id,
                "source": pdf_path.name,
                "pages": pages, 
                "num_blocks": len(related),
                "char_len": len(chunk_text),
            }
        })

        start = end - overlap

    return chunks


# ── 主扫描函数（同步，在 executor 里运行）────────────────────────────────────

def scan_and_index() -> None:
    docs_dir = config.DOCS_DIR
    if not docs_dir.exists():
        logger.info("docs/ not found, skipping RAG index scan.")
        return

    hashes: dict[str, str] = {}
    if HASH_FILE.exists():
        hashes = json.loads(HASH_FILE.read_text(encoding="utf-8"))

    collection = get_collection()
    updated = False

    for sub in sorted(docs_dir.iterdir()):
        if not sub.is_dir():
            continue
        collection_name = sub.name

        for pdf_path in sorted(sub.glob("*.pdf")):
            file_key = f"{collection_name}/{pdf_path.name}"
            current_hash = _md5(pdf_path)

            if hashes.get(file_key) == current_hash:
                continue  # 未变更，跳过

            logger.info(f"Indexing: {file_key}")

            # 删除旧 chunks（文件有改动时）
            if file_key in hashes:
                old = collection.get(where={"doc_id": file_key})
                if old["ids"]:
                    collection.delete(ids=old["ids"])
                    logger.info(f"  Removed {len(old['ids'])} old chunks.")

            chunks = _extract_chunks(pdf_path, collection_name)
            if not chunks:
                logger.warning(f"  No chunks extracted from {pdf_path.name}, skipping.")
                continue

            prefix = _safe_id(file_key)
            collection.add(
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
                ids=[f"{prefix}__{i}" for i in range(len(chunks))],
            )
            hashes[file_key] = current_hash
            updated = True
            logger.info(f"  Indexed {len(chunks)} chunks.")

    if updated:
        HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
        HASH_FILE.write_text(
            json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    logger.info(f"RAG scan complete. Total chunks: {collection.count()}")
