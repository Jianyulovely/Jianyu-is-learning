import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite

from db.models import DB_PATH
from core.memory_manage.memory_model import Memory, MemoryList, ExistingMemory
from core.memory_manage.utils import decode_keywords, merge_keywords


logger = logging.getLogger(__name__) 

class MemorySaver:
    async def save(self, user_id: int, memories: MemoryList) -> None:
        """对长期记忆进行去重更新"""
        if not memories.memories:
            return
        memories = memories.memories
        now_ts = int(datetime.now(ZoneInfo("Asia/Shanghai")).timestamp())
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                for memory in memories:
                    existing = await self._find_similar_memory(db, user_id, memory)
                    if existing:
                        await self._update_existing_memory(db, existing, memory, now_ts)
                    else:
                        await self._insert_memory(db, user_id, memory, now_ts)
                await db.commit()
        except Exception as exc:
            logger.warning("save_memories failed: %s", exc)
        
    async def _find_similar_memory(
        self,
        db: aiosqlite.Connection,
        user_id: int,
        memory: Memory,
    ) -> ExistingMemory | None:
        """
        1. 查找和已有记忆完全一致的内容
        2. 查找和已有记忆关键词有较高重复程度的内容 对于 event 添加时间接近的条件
        返回应该更新的那一条记忆
        """
        memory_type = memory.memory_type.value
        content = memory.content
        
        # 第一层：精确匹配
        async with db.execute(
            """
            SELECT id, memory_type, content, keywords_json, confidence, happened_at
            FROM long_term_memories
            WHERE user_id=? AND memory_type=? AND content=? AND status='active'
            LIMIT 1
            """,
            (user_id, memory_type, content),
        ) as cur:
            row = await cur.fetchone()
        if row:
            return ExistingMemory.model_validate(dict(row))

        # 第二层：关键词重合
        async with db.execute(
            """
            SELECT id, memory_type, content, keywords_json, confidence, happened_at
            FROM long_term_memories
            WHERE user_id=? AND memory_type=? AND status='active'
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            (user_id, memory_type),
        ) as cur:
            rows = await cur.fetchall()

        for row in rows:
            existing = ExistingMemory.model_validate(dict(row))
            existing_keywords = decode_keywords(existing.keywords_json)
            overlap = len(set(existing_keywords) & set(memory.keywords))
            if overlap >= 2:
                return existing
            if (
                memory.memory_type.value == "event"
                and memory.happened_ts
                and existing.happened_at
                and abs(existing.happened_at - memory.happened_ts) <= 86400
                and overlap >= 1
            ):
                return existing
        return None

    async def _update_existing_memory(
        self,
        db: aiosqlite.Connection,
        existing: ExistingMemory,
        memory: Memory,
        now_ts: int,
    ) -> None:
        """根据用户输入内容更新对应部分记忆"""

        # 置信度取两者最大值
        new_confidence = max(float(existing.confidence), float(memory.confidence))
        
        # 合并关键词
        existing_kws = decode_keywords(existing.keywords_json)
        merged_keywords = merge_keywords(existing_kws, memory.keywords)

        # 使用新时间
        happened_at = memory.happened_ts or existing.happened_at
        
        await db.execute(
            """
            UPDATE long_term_memories
            SET keywords_json=?,
                confidence=?,
                happened_at=?,
                updated_at=?,
                last_seen_at=?
            WHERE id=?
            """,
            (
                json.dumps(merged_keywords, ensure_ascii=False),
                new_confidence,
                happened_at,
                now_ts,
                now_ts,
                # 主键确定 更新内容即为主键所在记忆类别
                existing.id,
            ),
        )
    
    async def _insert_memory(
        self,
        db: aiosqlite.Connection,
        user_id: int,
        memory: Memory,
        now_ts: int,
    ) -> None:
        """添加用户相关长期记忆内容"""
        await db.execute(
            """
            INSERT INTO long_term_memories (
                user_id, memory_type, content, keywords_json, confidence,
                status, happened_at, created_at, updated_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                user_id,
                memory.memory_type.value,
                memory.content,
                # 字符串列表解析成 json 字符串存入
                json.dumps(memory.keywords, ensure_ascii=False),
                memory.confidence,
                memory.happened_ts,
                # 这三种时间这里没有进行区分，而是统一赋值，后续更改
                now_ts,
                now_ts,
                now_ts,
            ),
        )