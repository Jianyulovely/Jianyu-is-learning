import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite

from config import config
from core.net.http import safe_post
from core.models import ChatRequest
from core.memory_manage.utils import parse_llm_json_result
from core.memory_manage.memory_model import MemoryQueryContext, MemorySummary, ActiveMemory, ActiveMemoryList
from db.models import DB_PATH

logger = logging.getLogger(__name__)


_SUMMARY_SYSTEM_PROMPT = """
You are the long-term memory summarizer for companion-ai.

Your job:
- Read the user's current query.
- Read the user's active long-term memories.
- Select only memories that are useful for answering the current query.
- Return JSON that matches the MemorySummary schema exactly.

Rules:
- Do not invent facts.
- If a category has no useful memory for this query, return an empty string for that category.
- profile should contain stable facts about the user.
- preference should contain likes, dislikes, habits, and preferences.
- ongoing should contain current projects, goals, unresolved situations, or continuing context.
- event should contain dated events or plans that are relevant to the query.
- Use current_time_iso and timezone_name to judge whether ongoing/event memories are still relevant.
- Keep each field concise and directly usable in a system prompt.
""".strip()


class MemorySummarizer:
    async def summarize(self, memory_query: MemoryQueryContext) -> MemorySummary:
        user_memories = await self._get_memory(memory_query)
        if not user_memories.memories:
            return MemorySummary()
        return await self._call_llm(memory_query, user_memories)

    async def _get_memory(self, memory_query: MemoryQueryContext) -> ActiveMemoryList:
        """从 long_term_memory 数据库中获取指定用户的所有记忆"""

        timezone = memory_query.current_time.tzinfo
        def timestamp_to_iso(ts: int | None) -> str:
            """将时间戳转换为ISO字符串"""
            if ts is None:
                # 用户 profile 类记忆可能没有happened_at值，返回一个空字符串

                return ""
            else:
                return datetime.fromtimestamp(ts, timezone).isoformat()     

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, memory_type, content, happened_at, updated_at, last_seen_at
                    FROM long_term_memories
                    WHERE user_id=? AND status='active'
                    ORDER BY updated_at DESC
                    """,
                    (memory_query.user_id,),
                ) as cur:
                    rows = await cur.fetchall()
        except Exception as exc:
            logger.warning("get active memories failed: %s", exc)
            return ActiveMemoryList()

        memories: list[ActiveMemory] = []
        # 将用户长期记忆逐行填充到 ActiveMemoryList 中
        for row in rows:
            memory_type = row["memory_type"]
            content = row["content"] or ""
            if not content:
                continue
            happened_at_iso = ""
            updated_at_iso = ""
            last_seen_at_iso = ""

            # 将记忆中的时间戳转为可被直观理解的ISO字符串
            if memory_type == "ongoing":
                updated_at_iso = timestamp_to_iso(row["updated_at"])
                last_seen_at_iso = timestamp_to_iso(row["last_seen_at"])

            elif memory_type == "event":
                happened_at_iso = timestamp_to_iso(row["happened_at"])
                updated_at_iso = timestamp_to_iso(row["updated_at"])
                last_seen_at_iso = timestamp_to_iso(row["last_seen_at"])

            memories.append(
                ActiveMemory(
                    user_id=memory_query.user_id,
                    memory_type=memory_type,
                    content=content,
                    happened_at_iso=happened_at_iso,
                    updated_at_iso=updated_at_iso,
                    last_seen_at_iso=last_seen_at_iso,
                )
            )
        return ActiveMemoryList(memories=memories)


    async def _call_llm(
        self,
        memory_query: MemoryQueryContext,
        user_memories: ActiveMemoryList,
    ) -> MemorySummary:
        """调用llm进行用户query相关记忆检索"""
        summarize_prompt = (
            f"当前用户请求：\n{memory_query.query}\n\n"
            f"当前时间：\n{memory_query.current_time_iso}\n\n"
            f"当前用户相关记忆： \n{self._format_active_memories_table(user_memories)}\n\n"
        )
        req_payload = ChatRequest(
            system_prompt = _SUMMARY_SYSTEM_PROMPT,
            messages = [{"role": "user", "content": summarize_prompt}],
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "memory_summary",
                    "schema": MemorySummary.model_json_schema()
                }
            },
            temperature =  0.2,
            top_p =  0.9,
        ).model_dump()
        try:
            resp = await safe_post(f"{config.LLM_API_URL}/chat", json=req_payload, timeout=60.0)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("memory summary llm call failed: %s", exc)
            return MemorySummary()

        raw_summary = (resp.json().get("reply") or "").strip()
        # 解析json结果
        summary = parse_llm_json_result(raw_summary, MemorySummary, logger)

        return summary

    def _format_active_memories_table(self, user_memories: ActiveMemoryList) -> str:
        """将用户长期记忆转换为表格形式 显式给llm读取"""
        lines = [
            "| type | content | happened_at | updated_at | last_seen_at |",
            "|---|---|---|---|---|",
        ]
        for memory in user_memories.memories:
            lines.append(
                "| "
                f"{memory.memory_type.value} | "
                f"{memory.content} | "
                f"{memory.happened_at_iso} | "
                f"{memory.updated_at_iso} | "
                f"{memory.last_seen_at_iso} |"
            )
        return "\n".join(lines)
