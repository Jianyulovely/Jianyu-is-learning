import json
import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from config import config
from core.memory_manage.memory_model import MemoryExtractionResult
from core.http_client import safe_post
from db.models import DB_PATH

logger = logging.getLogger(__name__)


_ALLOWED_MEMORY_TYPES = {"profile", "preference", "ongoing", "event"}
_TYPE_BONUS = {
    "ongoing": 3.0,
    "preference": 2.0,
    "profile": 1.5,
    "event": 1.0,
}
_STOPWORDS = {
    "用户",
    "自己",
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "今天",
    "明天",
    "昨天",
    "最近",
    "现在",
    "刚刚",
    "一下",
    "已经",
    "还有",
    "就是",
    "真的",
    "感觉",
    "觉得",
}
_EXTRACTION_SYSTEM_PROMPT = """
你是 companion-ai 的长期记忆抽取器。

你的任务是从一轮对话中抽取“未来仍然值得记住的用户信息”。

只允许以下四类记忆：
1. profile: 相对稳定的背景资料
2. preference: 明确偏好、厌恶、习惯
3. ongoing: 持续一段时间的目标、计划、困扰、关系状态
4. event: 近期对后续对话可能重要的事件

不要记录：
- 寒暄
- 一次性小事实
- 助手自己的观点
- 不确定猜测
- 和用户无关的图片内容
- 仅适用于当前一句话、之后几乎没价值的内容

时间规则：
- 你会收到当前请求时间和时区。
- 如果用户提到今天、明天、下周三、月底等相对时间，尽量归一化到 happened_at。
- happened_at 必须是 ISO 8601 字符串，例如 2026-04-30T19:00:00+08:00。
- 如果时间无法可靠确定，happened_at 置为空字符串。
- 不要把时间戳硬塞进 content，除非时间本身就是关键事实的一部分。

输出要求：
- 只能输出 JSON
- 如果没有应保存的内容，输出 {"memories":[]}

输出格式：
{
  "memories": [
    {
      "memory_type": "profile|preference|ongoing|event",
      "content": "简洁中文陈述句，主语默认是用户",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.0,
      "happened_at": ""
    }
  ],
}
""".strip()


class MemoryService:
    async def build_memory_summary(
        self,
        user_id: int,
        current_message: str,
        limit: int = 6,
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> str:
        rows = await self.search_memories(
            user_id=user_id,
            query=current_message,
            limit=limit,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
        if not rows:
            return ""
        return self._format_summary(rows[:limit])

    async def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 8,
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> list[dict]:
        keywords = self._split_keywords(query)
        now_ts = self._current_timestamp(current_time_iso, timezone_name)
        rows: list[dict] = []

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, memory_type, content, keywords_json, confidence,
                           source, status, happened_at, created_at, updated_at, last_seen_at
                    FROM long_term_memories
                    WHERE user_id=? AND status='active'
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """,
                    (user_id,),
                ) as cur:
                    raw_rows = await cur.fetchall()
        except Exception as exc:
            logger.warning("search_memories failed: %s", exc)
            return []

        for row in raw_rows:
            item = dict(row)
            item["keywords"] = self._decode_keywords(item.get("keywords_json", "[]"))
            score, overlap = self._score_memory(item, keywords, now_ts)
            item["score"] = score
            item["overlap"] = overlap
            rows.append(item)

        matched = [row for row in rows if row["overlap"] > 0]
        if matched:
            matched.sort(key=lambda row: (row["score"], row["updated_at"]), reverse=True)
            return matched[:limit]

        fallback = [
            row for row in rows
            if row["memory_type"] in {"ongoing", "preference", "profile"}
            and float(row.get("confidence") or 0.0) >= 0.75
        ]
        fallback.sort(key=lambda row: (row["score"], row["updated_at"]), reverse=True)
        return fallback[: min(limit, 3)]

    async def extract_candidate_memories(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
        image_context: str = "",
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> list[dict]:
        prompt = self._build_extraction_prompt(
            user_message=user_message,
            assistant_reply=assistant_reply,
            image_context=image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
        raw = await self._call_llm(prompt)
        data = self._safe_parse_json(raw)
        memories = data.get("memories", []) if isinstance(data, dict) else []
        return self._filter_candidates(memories, timezone_name=timezone_name)

    async def save_memories(self, user_id: int, memories: list[dict]) -> None:
        if not memories:
            return

        now_ts = datetime.now(ZoneInfo("Asia/Shanghai")).timestamp()
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

    async def after_turn(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
        image_context: str = "",
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> None:
        try:
            memories = await self.extract_candidate_memories(
                user_id=user_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
                image_context=image_context,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )
            if memories:
                await self.save_memories(user_id=user_id, memories=memories)
        except Exception as exc:
            logger.warning("after_turn failed: %s", exc)

    def _build_extraction_prompt(
        self,
        user_message: str,
        assistant_reply: str,
        image_context: str,
        current_time_iso: str,
        timezone_name: str,
    ) -> str:
        image_block = image_context or "无"
        return (
            f"当前请求时间：\n{current_time_iso or '未知'}\n\n"
            f"时区：\n{timezone_name}\n\n"
            f"用户输入：\n{user_message}\n\n"
            f"助手回复：\n{assistant_reply}\n\n"
            f"图片上下文：\n{image_block}\n\n"
            "请抽取应该进入长期记忆的用户信息。"
        )

    async def _call_llm(self, prompt: str) -> str:
        payload = {
            "system_prompt": _EXTRACTION_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": MemoryExtractionResult.model_json_schema(),
            "temperature": 0.2,
            "top_p": 0.9,
        }
        resp = await safe_post(f"{config.LLM_API_URL}/chat", json=payload, timeout=60.0)
        resp.raise_for_status()
        return (resp.json().get("reply") or "").strip()

    def _safe_parse_json(self, raw: str) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.S)
            if not match:
                logger.warning("memory extractor returned non-json: %r", raw[:300])
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("memory extractor json parse failed: %r", raw[:300])
                return {}

    def _filter_candidates(self, memories: list[dict], timezone_name: str) -> list[dict]:
        results: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for memory in memories or []:
            if not isinstance(memory, dict):
                continue
            normalized = self._normalize_candidate(memory, timezone_name)
            if not normalized:
                continue
            key = (normalized["memory_type"], self._normalize_text(normalized["content"]))
            if key in seen:
                continue
            seen.add(key)
            results.append(normalized)
        return results

    def _normalize_candidate(self, memory: dict, timezone_name: str) -> dict | None:
        memory_type = str(memory.get("memory_type", "")).strip().lower()
        if memory_type not in _ALLOWED_MEMORY_TYPES:
            return None

        content = str(memory.get("content", "")).strip()
        if not content:
            return None

        confidence = self._clamp_confidence(memory.get("confidence", 0.0))
        if confidence < 0.65:
            return None

        keywords = [
            str(keyword).strip()
            for keyword in (memory.get("keywords") or [])
            if str(keyword).strip()
        ]
        if not keywords:
            keywords = self._split_keywords(content)
        keywords = keywords[:5]

        happened_at = self._parse_happened_at(memory.get("happened_at", ""), timezone_name)
        if memory_type in {"profile", "preference"}:
            happened_at = None

        return {
            "memory_type": memory_type,
            "content": content,
            "keywords": keywords,
            "confidence": confidence,
            "happened_at": happened_at,
            "source": "chat",
        }

    async def _find_similar_memory(
        self,
        db: aiosqlite.Connection,
        user_id: int,
        memory: dict,
    ) -> dict | None:
        async with db.execute(
            """
            SELECT id, memory_type, content, keywords_json, confidence, happened_at
            FROM long_term_memories
            WHERE user_id=? AND memory_type=? AND content=? AND status='active'
            LIMIT 1
            """,
            (user_id, memory["memory_type"], memory["content"]),
        ) as cur:
            row = await cur.fetchone()
        if row:
            return dict(row)

        async with db.execute(
            """
            SELECT id, memory_type, content, keywords_json, confidence, happened_at
            FROM long_term_memories
            WHERE user_id=? AND memory_type=? AND status='active'
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            (user_id, memory["memory_type"]),
        ) as cur:
            rows = await cur.fetchall()

        for row in rows:
            existing = dict(row)
            existing_keywords = self._decode_keywords(existing.get("keywords_json", "[]"))
            overlap = len(set(existing_keywords) & set(memory["keywords"]))
            if overlap >= 2:
                return existing
            if (
                memory["memory_type"] == "event"
                and memory.get("happened_at")
                and existing.get("happened_at")
                and abs(float(existing["happened_at"]) - float(memory["happened_at"])) <= 86400
                and overlap >= 1
            ):
                return existing
        return None

    async def _update_existing_memory(
        self,
        db: aiosqlite.Connection,
        existing: dict,
        memory: dict,
        now_ts: float,
    ) -> None:
        new_confidence = max(
            float(existing.get("confidence") or 0.0),
            float(memory.get("confidence") or 0.0),
        )
        merged_keywords = self._merge_keywords(
            self._decode_keywords(existing.get("keywords_json", "[]")),
            memory["keywords"],
        )
        happened_at = memory.get("happened_at") or existing.get("happened_at")
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
                existing["id"],
            ),
        )

    async def _insert_memory(
        self,
        db: aiosqlite.Connection,
        user_id: int,
        memory: dict,
        now_ts: float,
    ) -> None:
        await db.execute(
            """
            INSERT INTO long_term_memories (
                user_id, memory_type, content, keywords_json, confidence,
                source, status, happened_at, created_at, updated_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                user_id,
                memory["memory_type"],
                memory["content"],
                json.dumps(memory["keywords"], ensure_ascii=False),
                memory["confidence"],
                memory.get("source", "chat"),
                memory.get("happened_at"),
                now_ts,
                now_ts,
                now_ts,
            ),
        )

    def _score_memory(self, item: dict, query_keywords: list[str], now_ts: float) -> tuple[float, int]:
        overlap = 0
        content = str(item.get("content") or "")
        row_keywords = set(item.get("keywords") or [])
        query_set = set(query_keywords)

        if query_set:
            overlap = len(row_keywords & query_set)
            if overlap == 0:
                overlap = sum(1 for keyword in query_set if keyword and keyword in content)

        score = overlap * 10.0
        score += _TYPE_BONUS.get(item.get("memory_type", ""), 0.0)
        score += float(item.get("confidence") or 0.0)

        updated_at = float(item.get("updated_at") or 0.0)
        happened_at = item.get("happened_at")
        if item.get("memory_type") == "event":
            score += self._event_time_bonus(happened_at, now_ts)
            if overlap == 0:
                score -= 3.0
        elif item.get("memory_type") == "ongoing":
            score += self._recentness_bonus(updated_at, now_ts, max_days=30)
        else:
            score += self._recentness_bonus(updated_at, now_ts, max_days=90) * 0.5

        return score, overlap

    def _event_time_bonus(self, happened_at: Any, now_ts: float) -> float:
        if happened_at in (None, ""):
            return 0.0
        try:
            delta = float(happened_at) - now_ts
        except (TypeError, ValueError):
            return 0.0

        day = 86400.0
        if 0 <= delta <= 7 * day:
            return 5.0
        if 7 * day < delta <= 30 * day:
            return 2.5
        if -3 * day <= delta < 0:
            return 1.5
        if delta < -30 * day:
            return -4.0
        if delta < -7 * day:
            return -2.0
        return 0.0

    def _recentness_bonus(self, ts: float, now_ts: float, max_days: int) -> float:
        if not ts:
            return 0.0
        age_days = max((now_ts - ts) / 86400.0, 0.0)
        if age_days >= max_days:
            return 0.0
        return max(0.0, 2.0 - (age_days / max_days) * 2.0)

    def _format_summary(self, rows: list[dict]) -> str:
        labels = {
            "ongoing": "用户近况",
            "preference": "用户偏好",
            "profile": "用户背景",
            "event": "近期事件",
        }
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["memory_type"], []).append(str(row["content"]))

        parts: list[str] = []
        for memory_type in ("ongoing", "preference", "profile", "event"):
            items = grouped.get(memory_type)
            if not items:
                continue
            unique_items = list(dict.fromkeys(items))
            parts.append(f"{labels[memory_type]}：" + "；".join(unique_items[:2]))
        return "\n".join(parts)

    def _split_keywords(self, text: str) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_]{2,32}", text or "")
        results: list[str] = []
        for token in tokens:
            token = token.strip().lower()
            if not token or token in _STOPWORDS:
                continue
            if token not in results:
                results.append(token)
        return results[:8]

    def _decode_keywords(self, raw: str) -> list[str]:
        try:
            data = json.loads(raw or "[]")
        except json.JSONDecodeError:
            return []
        results: list[str] = []
        for item in data:
            token = str(item).strip().lower()
            if token and token not in results:
                results.append(token)
        return results

    def _merge_keywords(self, left: list[str], right: list[str]) -> list[str]:
        merged: list[str] = []
        for token in left + right:
            normalized = str(token).strip().lower()
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged[:8]

    def _parse_happened_at(self, value: Any, timezone_name: str) -> float | None:
        if value in (None, "", 0):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            pass
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(timezone_name))
            return dt.timestamp()
        except ValueError:
            return None

    def _current_timestamp(self, current_time_iso: str, timezone_name: str) -> float:
        parsed = self._parse_happened_at(current_time_iso, timezone_name)
        if parsed is not None:
            return parsed
        return datetime.now(ZoneInfo(timezone_name)).timestamp()

    def _clamp_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0
        return max(0.0, min(confidence, 1.0))

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())
