import logging
import json
from typing import Any
from zoneinfo import ZoneInfo
import aiosqlite

from core.memory_manage.memory_model import *
from core.memory_manage.utils import decode_keywords

from db.models import DB_PATH

logger = logging.getLogger(__name__)

_ALLOWED_MEMORY_TYPES = {"profile", "preference", "ongoing", "event"}
_TYPE_BONUS = {
    "ongoing": 3.0,
    "preference": 2.0,
    "profile": 1.5,
    "event": 1.0,
}

class MemorySummarizer:

    async def summarize(self, memory_query: MemoryQueryContext) -> list[dict]:
        keywords = self._split_keywords(memory_query.query)
        now_ts = self._current_timestamp(
            memory_query.current_time_iso,
            memory_query.timezone_name
        )
        rows: list[dict] = []

        # 先获取有关于该用户的全部记忆
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, memory_type, content, keywords_json, confidence,
                        status, happened_at, created_at, updated_at, last_seen_at
                    FROM long_term_memories
                    WHERE user_id=? AND status='active'
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """,
                    (memory_query.user_id,),
                ) as cur:
                    raw_rows = await cur.fetchall()
        except Exception as exc:
            logger.warning("search_memories failed: %s", exc)
            return []

        for row in raw_rows:
            item = dict(row)
            item["keywords"] = decode_keywords(item.get("keywords_json", "[]"))
            score, overlap = self._score_memory(item, keywords, now_ts)
            item["score"] = score
            item["overlap"] = overlap
            rows.append(item)

        matched = [row for row in rows if row["overlap"] > 0]
        if matched:
            matched.sort(key=lambda row: (row["score"], row["updated_at"]), reverse=True)
            return matched[:memory_query.limit]

        fallback = [
            row for row in rows
            if row["memory_type"] in {"ongoing", "preference", "profile"}
            and float(row.get("confidence") or 0.0) >= 0.75
        ]
        fallback.sort(key=lambda row: (row["score"], row["updated_at"]), reverse=True)
        return fallback[: min(memory_query.limit, 3)]

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

    def _current_timestamp(self, current_time_iso: str, timezone_name: str) -> float:
        parsed = self._parse_happened_at(current_time_iso, timezone_name)
        if parsed is not None:
            return parsed
        return datetime.now(ZoneInfo(timezone_name)).timestamp()