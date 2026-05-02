# Long-Term Memories Schema V1

## Goal

Define a clean SQLite schema for long-term memory in `companion-ai`.

This schema is for V1 only:

- simple
- explicit
- easy to query
- easy to evolve later

It should not reuse the current generic `memories` table as the primary long-term memory store.

Reason:

- current `memories` is too weak semantically
- it is already being used like a generic image-description sink
- long-term memory needs typed fields and update semantics

## Suggested New Table

Recommended table name:

- `long_term_memories`

Suggested SQL:

```sql
CREATE TABLE IF NOT EXISTS long_term_memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    memory_type     TEXT NOT NULL,          -- profile | preference | ongoing | event
    content         TEXT NOT NULL,          -- normalized human-readable statement
    keywords_json   TEXT NOT NULL DEFAULT '[]',
    confidence      REAL NOT NULL DEFAULT 0.8,
    source          TEXT NOT NULL DEFAULT 'chat',   -- chat | image | manual
    status          TEXT NOT NULL DEFAULT 'active', -- active | superseded | deleted
    happened_at     REAL,                          -- optional event time
    created_at      REAL NOT NULL DEFAULT (unixepoch()),
    updated_at      REAL NOT NULL DEFAULT (unixepoch()),
    last_seen_at    REAL NOT NULL DEFAULT (unixepoch())
);
```

## Suggested Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_ltm_user_id
ON long_term_memories(user_id);

CREATE INDEX IF NOT EXISTS idx_ltm_user_type_status
ON long_term_memories(user_id, memory_type, status);

CREATE INDEX IF NOT EXISTS idx_ltm_user_updated
ON long_term_memories(user_id, updated_at DESC);
```

V1 does not need complex indexing yet.

If retrieval becomes slow later, add:

- FTS virtual table for `content`
- optional keyword index table

## Field Meaning

### `user_id`

Which user this memory belongs to.

### `memory_type`

Allowed values:

- `profile`
- `preference`
- `ongoing`
- `event`

Recommended meaning:

- `profile`: stable background, identity, long-lived facts
- `preference`: likes, dislikes, habits, recurring tastes
- `ongoing`: current goal, plan, problem, relationship state
- `event`: recent event worth remembering later

### `content`

Normalized memory text.

Examples:

- `用户在上海工作`
- `用户喜欢英短猫`
- `用户最近在准备考研`
- `用户下周有面试`

Requirements:

- short
- explicit
- reusable in later prompt summaries
- one fact per row when possible

### `keywords_json`

JSON array of keywords for cheap retrieval in V1.

Examples:

```json
["上海", "工作"]
["英短猫", "喜欢", "宠物"]
["考研", "备考", "最近"]
```

### `confidence`

How reliable the extracted memory is.

Suggested V1 rule:

- below `0.65`: usually do not save
- `0.65` to `0.8`: save carefully
- above `0.8`: normal save

### `source`

Where the memory came from.

Suggested values:

- `chat`
- `image`
- `manual`

This helps later debugging and filtering.

### `status`

Lifecycle state of the memory.

Suggested values:

- `active`
- `superseded`
- `deleted`

Why this matters:

- you do not always want to hard-delete old memory
- `ongoing` memories may be replaced by a newer state

Example:

- old: `用户最近在找工作`
- new: `用户已经入职新公司`

The old row can become `superseded`.

### `happened_at`

When the event actually happens or started to happen.

This is different from storage time.

Examples:

- user says today: `我下周三面试`
- `created_at`: today
- `happened_at`: next Wednesday

Recommended usage:

- mainly for `event`
- optional for `ongoing`
- usually empty for `profile` and `preference`

### `created_at`

When the row was first created.

### `updated_at`

When the row was last modified.

### `last_seen_at`

When the same or similar fact was last reconfirmed in conversation.

This is useful later for:

- ranking
- decay
- cleanup

## Temporal Awareness Design

For `companion-ai`, time awareness should be treated as first-class memory metadata.

Why:

- users frequently speak in relative time: `今天`, `明天`, `最近`, `下周`
- event relevance changes quickly over time
- without time fields, the agent will keep surfacing stale memories

Recommended time model in V1:

- `created_at`: memory ingestion time
- `updated_at`: last write/update time
- `last_seen_at`: last reconfirmation time
- `happened_at`: event occurrence time

These four fields solve different problems and should not be collapsed into one timestamp.

## Retrieval Rules With Time

Suggested V1 ranking factors:

1. `status = active`
2. keyword overlap count
3. memory type priority
4. time relevance
5. `confidence`

Time relevance guidance:

- future events should be boosted
- very recent past events may still be relevant
- stale old events should be downgraded
- ongoing states should prefer rows with newer `updated_at`

Minimal V1 heuristics:

- if `memory_type = event` and `happened_at` is far in the past, lower score
- if `memory_type = event` and `happened_at` is in the near future, raise score
- if `memory_type = ongoing`, prefer more recently updated rows
- if `memory_type = preference` or `profile`, do not over-penalize by age

## Optional Companion Table

If you want image memory to be more structured later, add a second table instead of overloading long-term memory rows.

Recommended optional table:

- `image_observations`

Example:

```sql
CREATE TABLE IF NOT EXISTS image_observations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    file_hash       TEXT NOT NULL,
    telegram_file_id TEXT,
    caption         TEXT NOT NULL DEFAULT '',
    vision_summary  TEXT NOT NULL,
    extracted_fact  TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL DEFAULT (unixepoch())
);
```

This table is optional for V1.

If you want the leanest path, skip it first.

## Recommended Migration Strategy

Keep the existing `memories` table for now.

Do not delete or rewrite it in V1.

Instead:

1. add `long_term_memories`
2. make `MemoryService` write only to `long_term_memories`
3. gradually stop relying on the old `memories` table for new product logic

This is safer because:

- existing code keeps working
- migration risk stays low
- rollback is easy

## Retrieval Strategy for V1

V1 retrieval should stay simple and deterministic.

Suggested ranking factors:

1. `status = active`
2. keyword overlap count
3. `memory_type` priority
4. `updated_at` recency
5. `confidence`

Recommended priority by type:

1. `ongoing`
2. `preference`
3. `profile`
4. `event`

Reason:

- ongoing state usually has the highest short-term personalization value

Time can refine this priority.

Example:

- an upcoming interview event may outrank an old stable preference for one or two days

## Example Rows

```text
user_id=1001
memory_type=profile
content=用户在上海工作
keywords_json=["上海","工作"]
confidence=0.92
source=chat
status=active
```

```text
user_id=1001
memory_type=preference
content=用户喜欢英短猫
keywords_json=["英短猫","喜欢","宠物"]
confidence=0.88
source=chat
status=active
```

```text
user_id=1001
memory_type=ongoing
content=用户最近在准备考研
keywords_json=["考研","备考","最近"]
confidence=0.94
source=chat
status=active
```

```text
user_id=1001
memory_type=event
content=用户下周三有面试
keywords_json=["面试","下周三"]
confidence=0.90
source=chat
status=active
happened_at=1774780800
```

## Save Rules for V1

When saving a new memory:

1. reject if `content` is empty
2. reject if `memory_type` is invalid
3. reject if `confidence < 0.65`
4. exact same `user_id + memory_type + content + status=active` -> do not insert again
5. high similarity -> update `updated_at`, `last_seen_at`, and maybe `confidence`
6. new ongoing state that clearly replaces an old one -> mark old row `superseded`

Additional time rule:

7. if the same event is mentioned again with a clearer time, update `happened_at`

## Time Extraction Guidance

Recommended V1 behavior for time extraction:

1. absolute time mentioned by user -> store directly
2. relative time mentioned by user -> normalize using current request time and timezone
3. vague time only -> keep memory content but leave `happened_at` empty
4. never invent precise timestamps from ambiguous phrases

Examples:

- `我明天去医院`
  - good to store as `event`
  - resolve `happened_at` if current request time is known

- `我最近睡不好`
  - good to store as `ongoing`
  - no need for exact `happened_at`

- `我以前在北京读书`
  - may be `profile`
  - `happened_at` optional and usually unnecessary

## Prompt-Time Awareness Recommendation

Long-term memory alone is not enough.

The agent should also receive current request time in the main system prompt on every turn.

Minimal injected line:

```text
当前时间是 2026-04-27T20:15:00+08:00，时区是 Asia/Shanghai。
```

This helps the model interpret:

- `今天`
- `明天`
- `周末`
- `月底`
- `下周`

It also reduces contradictions between reply generation and memory extraction.

## What Not To Add Yet

Do not add these in V1 unless they are immediately needed:

- embedding columns
- vector ids
- graph edges
- reflection summaries
- memory importance decay jobs
- per-memory access counters

Those belong to a later iteration.

## Recommended Next Step

After this schema is accepted:

1. update `db/models.py`
2. add `core/memory_service.py`
3. minimally wire `bot/handler.py`
4. test retrieval and post-turn extraction with a few real conversations
