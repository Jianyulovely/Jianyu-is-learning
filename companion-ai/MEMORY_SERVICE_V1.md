# MemoryService V1

## Goal

Build a minimal long-term memory layer for `companion-ai` without replacing the current sliding-window memory.

V1 principles:

- Keep current short-term memory unchanged.
- Use SQLite as the primary long-term memory store.
- Start with rule-based and keyword-based retrieval.
- Reuse the existing `PromptEngine.build_system_prompt(..., memory_summary=...)` hook.
- Run memory extraction asynchronously after each turn.
- Add minimal temporal awareness so memory can distinguish "recorded time" from "event time".

## Current Context

Existing short-term memory:

- Redis cache + SQLite conversation persistence in `core/session_manager.py`
- Sliding-window history is already stable enough for V1

Existing prompt hook:

- `core/prompt_engine.py` already supports:
  - `memory_summary`
  - `image_context`

Main bot entry:

- `bot/handler.py::_handle_message(...)`

## Service Responsibility

`MemoryService` should do only four things in V1:

1. Retrieve relevant long-term memories for the current user message
2. Build a short memory summary string for prompt injection
3. Extract candidate memories from the completed turn
4. Deduplicate and save them into SQLite

It should not do the following in V1:

- vector search
- embeddings
- complex memory scoring pipelines
- memory reflection
- memory graph
- full mem0-style orchestration

## Suggested File

Create:

- `core/memory_service.py`

## Suggested Data Shape

Each candidate memory should use this minimal structure:

```python
{
    "memory_type": "profile|preference|ongoing|event",
    "content": "用户最近在准备考研",
    "keywords": ["考研", "备考", "最近"],
    "confidence": 0.91,
    "happened_at": "2026-04-30T19:00:00+08:00",  # optional
}
```

Meaning of memory types:

- `profile`: relatively stable user background
- `preference`: likes, dislikes, habits, recurring choices
- `ongoing`: ongoing goal, plan, trouble, project, relationship state
- `event`: recent event that may matter in later dialogue

`happened_at` meaning:

- when the event actually happens or starts to matter
- optional in V1
- mainly useful for `event`
- sometimes useful for `ongoing`

## Suggested Class Interface

```python
class MemoryService:
    async def build_memory_summary(
        self,
        user_id: int,
        current_message: str,
        limit: int = 6,
    ) -> str:
        """Return a short memory summary for system prompt injection."""

    async def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 8,
    ) -> list[dict]:
        """Retrieve candidate memories by keyword and simple ranking."""

    async def extract_candidate_memories(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
        image_context: str = "",
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> list[dict]:
        """Use an LLM to extract long-term memory candidates from one turn."""

    async def save_memories(
        self,
        user_id: int,
        memories: list[dict],
    ) -> None:
        """Deduplicate and persist memories."""

    async def after_turn(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
        image_context: str = "",
        current_time_iso: str = "",
        timezone_name: str = "Asia/Shanghai",
    ) -> None:
        """Async post-turn entry point called by handler."""
```

## Pseudocode

### `build_memory_summary`

```python
async def build_memory_summary(user_id, current_message, limit=6):
    rows = await self.search_memories(
        user_id=user_id,
        query=current_message,
        limit=limit,
    )

    if not rows:
        return ""

    # Group by memory_type and compress into short natural-language lines.
    # Keep it short to avoid prompt bloat.
    #
    # Example:
    # 偏好：喜欢英短猫、晚上聊天更多
    # 近况：最近在准备考研
    # 背景：在上海工作
    return self._format_summary(rows)
```

### `search_memories`

```python
async def search_memories(user_id, query, limit=8):
    keywords = self._split_keywords(query)

    # V1 retrieval:
    # 1. content LIKE query keyword
    # 2. keyword overlap count
    # 3. recency and confidence bonus
    rows = await self._query_sqlite(user_id, keywords, limit=limit * 3)

    ranked = self._rank_rows(rows, keywords)
    return ranked[:limit]
```

### `extract_candidate_memories`

```python
async def extract_candidate_memories(
    user_id,
    user_message,
    assistant_reply,
    image_context="",
    current_time_iso="",
    timezone_name="Asia/Shanghai",
):
    prompt = self._build_extraction_prompt(
        user_message=user_message,
        assistant_reply=assistant_reply,
        image_context=image_context,
        current_time_iso=current_time_iso,
        timezone_name=timezone_name,
    )

    raw = await self._call_json_llm(prompt)
    data = self._safe_parse_json(raw)

    if not data:
        return []

    memories = data.get("memories", [])

    # Drop bad candidates:
    # - empty content
    # - unsupported type
    # - low confidence
    # - pure small talk
    # - assistant-only facts
    return self._filter_candidates(memories)
```

### `save_memories`

```python
async def save_memories(user_id, memories):
    for mem in memories:
        existing = await self._find_similar_memory(user_id, mem)

        if existing is None:
            await self._insert_memory(user_id, mem)
            continue

        # V1 merge strategy:
        # - exact same content: skip or bump metadata
        # - same type + high keyword overlap: update confidence/timestamps
        # - ongoing memories may replace stale state
        await self._merge_into_existing(existing, mem)
```

### `after_turn`

```python
async def after_turn(
    user_id,
    user_message,
    assistant_reply,
    image_context="",
    current_time_iso="",
    timezone_name="Asia/Shanghai",
):
    memories = await self.extract_candidate_memories(
        user_id=user_id,
        user_message=user_message,
        assistant_reply=assistant_reply,
        image_context=image_context,
        current_time_iso=current_time_iso,
        timezone_name=timezone_name,
    )

    if not memories:
        return

    await self.save_memories(user_id=user_id, memories=memories)
```

## Minimal Internal Helpers

Recommended private helpers:

```python
def _split_keywords(self, text: str) -> list[str]: ...
def _format_summary(self, rows: list[dict]) -> str: ...
def _safe_parse_json(self, raw: str) -> dict: ...
def _filter_candidates(self, memories: list[dict]) -> list[dict]: ...
def _now_iso(self) -> str: ...
async def _find_similar_memory(self, user_id: int, memory: dict) -> dict | None: ...
async def _insert_memory(self, user_id: int, memory: dict) -> None: ...
async def _merge_into_existing(self, existing: dict, memory: dict) -> None: ...
```

## Temporal Awareness V1

This part is worth adding now.

Without temporal awareness, memory quality drops quickly:

- old events keep being retrieved after they no longer matter
- relative time phrases like `明天` or `下周三` become ambiguous
- the agent cannot tell whether a fact is fresh or stale

V1 time-awareness scope should stay narrow:

1. pass current request time into the extractor
2. normalize relative time expressions into ISO timestamps when possible
3. store `happened_at` separately from `created_at`
4. prefer fresher memories during retrieval
5. suppress expired short-lived events in prompt summaries

Recommended distinction:

- `created_at`: when the memory row was first written
- `updated_at`: when the row was last updated
- `last_seen_at`: when the user last reconfirmed it
- `happened_at`: when the event actually happens

Example:

- user says on `2026-04-27 20:00 +08:00`: `我下周三面试`
- memory `content`: `用户下周三有面试`
- `created_at`: `2026-04-27T20:00:00+08:00`
- `happened_at`: `2026-04-29T00:00:00+08:00` or a more precise time if available

## Retrieval Rules With Time

Recommended V1 behavior:

1. `profile` and `preference` are mostly timeless
2. `ongoing` should prefer newer rows
3. `event` should strongly depend on `happened_at` and recency

Suggested heuristics:

- future upcoming events: boost retrieval
- very recent events: allow retrieval
- old past events: lower rank unless reconfirmed recently
- expired reminders: do not inject into prompt summary

Examples:

- `用户明天有考试`
  - before exam: high value
  - two weeks after exam: low value unless user is still discussing it

- `用户最近在准备考研`
  - still useful for a long time
  - keep active until superseded

## Minimal Time Context In Handler

Even in V1, the agent should know the current request time.

Recommended addition in `bot/handler.py` before prompt building and memory extraction:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

tz_name = "Asia/Shanghai"
current_time_iso = datetime.now(ZoneInfo(tz_name)).isoformat()
```

Use it in two places:

1. pass it to memory extraction
2. inject one short line into the system prompt

Example prompt line:

```text
当前时间是 2026-04-27T20:15:00+08:00，时区是 Asia/Shanghai。
```

This improves:

- understanding of `今天/明天/下周`
- handling of schedule-like conversations
- temporal consistency in replies

## Dedup Rules for V1

Keep dedup simple:

1. same `user_id`
2. same `memory_type`
3. exact same `content` -> skip insert
4. high keyword overlap -> update existing row
5. `ongoing` memories may overwrite stale state when the new statement is clearly fresher

Examples:

- old: `用户最近在找工作`
- new: `用户已经拿到 offer`

This should update or deactivate the older `ongoing` state instead of storing both as equal truths.

## Minimal Handler Wiring

The current handler path is already suitable for V1.

In `bot/handler.py`:

1. Initialize the service once

```python
from core.memory_service import MemoryService

_memory_service = MemoryService()
```

2. Before building the system prompt, retrieve image context and memory summary

```python
image_context = ""
if not images:
    image_context = await _session.get_last_image_desc(user_id)

memory_summary = await _memory_service.build_memory_summary(
    user_id=user_id,
    current_message=user_message,
)
```

3. Reuse the existing prompt hook

```python
system_prompt = _prompt_engine.build_system_prompt(
    role_id=role_id,
    user_name=user_name,
    emotion=emotion,
    intimacy_level=intimacy,
    image_context=image_context,
    memory_summary=memory_summary,
)
```

4. After the reply is generated and appended, run post-turn extraction asynchronously

```python
asyncio.create_task(
    _memory_service.after_turn(
        user_id=user_id,
        user_message=user_message,
        assistant_reply=reply,
        image_context=image_context,
        current_time_iso=current_time_iso,
        timezone_name=tz_name,
    )
)
```

## Image Handling Recommendation for V1

Do not automatically write every image description into long-term memory.

Current image flow stores:

- Redis `last_image_desc`
- SQLite `memories`

Suggested V1 behavior:

- keep `set_last_image_desc(...)`
- stop treating every image description as long-term memory by default
- let `MemoryService.after_turn(...)` decide whether image-related information is worth saving

Reason:

- many images are only relevant to the current turn
- long-term memory should store user-relevant facts, not raw scene descriptions

## Extraction Prompt Draft

Recommended system prompt:

```text
You are the long-term memory extractor for companion-ai.

Task:
Extract user information from the current turn that is valuable for future personalized companionship.

Only keep these four categories:
1. profile
2. preference
3. ongoing
4. event

Do not store:
- small talk
- one-off trivial facts
- assistant opinions
- uncertain guesses
- overly sensitive information unless clearly necessary for future companionship
- image descriptions that do not reveal user-relevant facts

Time rules:
- You are given the current request time and timezone.
- If the user mentions relative time such as 今天、明天、下周三、月底, normalize it when possible.
- Put normalized event time into `happened_at`.
- If time cannot be resolved reliably, set `happened_at` to an empty string.
- Do not put timestamps inside `content` unless the time itself is the key fact.

Output rules:
- return JSON only
- if nothing should be stored, return {"memories":[]}

Output format:
{
  "memories": [
    {
      "memory_type": "profile|preference|ongoing|event",
      "content": "简洁中文陈述句，主语默认是用户",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.0,
      "happened_at": ""
    }
  ]
}
```

Recommended user template:

```text
当前请求时间：
{{current_time_iso}}

时区：
{{timezone_name}}

用户输入：
{{user_message}}

助手回复：
{{assistant_reply}}

图片上下文：
{{image_context}}

请抽取应该进入长期记忆的用户信息。
```

## Time Parsing Policy

Recommended V1 parsing policy:

1. if the user gives an absolute date or datetime, preserve it
2. if the user gives a relative time and current request time is known, normalize it
3. if only a vague period is known, keep `content` but leave `happened_at` empty
4. never fabricate precise time from weak clues

Examples:

- `我明天下午面试`
  - `content`: `用户明天下午有面试`
  - `happened_at`: resolve if extractor can do so reliably

- `我最近在找房子`
  - `content`: `用户最近在找房子`
  - `happened_at`: empty

- `我 5 月 8 号去杭州`
  - `content`: `用户 5 月 8 号去杭州`
  - `happened_at`: `2026-05-08T00:00:00+08:00` if year can be inferred from current request time

## V1 Boundaries

This design is intentionally conservative.

Do first:

- stable schema
- basic retrieval
- short prompt summary
- async extraction

Do later in V1.5 or V2:

- embeddings
- vector retrieval
- memory decay
- contradiction resolution beyond simple rules
- explicit memory editing by the user
