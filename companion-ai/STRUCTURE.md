# Companion AI Structure

This project is split by feature ownership. Keep entrypoints thin, keep shared
contracts explicit, and avoid placing new feature code directly in `core/`.

## Top-Level Directories

- `main.py`: Telegram bot runtime entrypoint. Wires the bus, session manager,
  agent service, database initialization, startup/shutdown.
- `bot/`: Channel adapter layer. Telegram-specific commands, update parsing,
  outbound delivery live here.
- `core/`: Product and application logic. Code here must not depend on
  Telegram-specific types.
- `llm/`: FastAPI service exposing local model endpoints (`/chat`, `/generate`,
  `/health`).
- `db/`: Persistence adapters for SQLite and Redis.
- `roles/`: Persona YAML files.
- `data/`: Local runtime data (SQLite databases, vector indexes). Not committed.
- `tests/`: pytest suite. Coroutines run via `asyncio.run` from `conftest.py`,
  no pytest-asyncio dependency.

## Core Feature Groups

```
core/
├── agent_service.py          # Thin Flow router + session/telegram glue
│
├── agent/                    # Agent runtime: layered (mirrors OpenManus app/agent/)
│   ├── base.py               #   BaseAgent: state machine + run/step loop
│   ├── react.py              #   ReActAgent: think + act split
│   ├── toolcall.py           #   ToolCallAgent: LLM-driven tool loop
│   ├── chat_agent.py         #   ChatAgent: companion-flavoured ToolCallAgent
│   ├── state.py              #   AgentTaskState (Pydantic model, persisted in Redis)
│   ├── store.py              #   Redis-backed task storage
│   ├── context.py            #   prepare_agent_context: role / prompt / image desc
│   ├── helpers.py            #   message helpers, role loader, ToolArgumentError
│   └── formatter.py          #   reply formatting (LaTeX → Unicode, HTML)
│
├── flow/                     # Turn-level orchestration (mirrors OpenManus app/flow/)
│   ├── base.py               #   BaseFlow + FlowOutcome
│   ├── chat.py               #   ChatFlow: single ChatAgent for casual / single task
│   ├── planning.py           #   PlanningFlow: multi-step plan executor
│   └── router.py             #   Control-command detection (cancel/continue/status)
│
├── planning/                 # Plan data + builder (legacy decide/create stage)
│   ├── models.py             #   PlanState, PlanStep, mark_plan_step
│   ├── formatter.py          #   format_plan_text
│   └── flow.py               #   PlanBuilder (imported as ``PlanBuilder`` from flow/)
│
├── tool/                     # Tool framework + concrete tools
│   ├── base.py, tool_collection.py
│   ├── ask_human.py, terminate.py
│   ├── planning.py           #   PlanningTool (stage-aware: create vs execute)
│   ├── file_editor/          #   StrReplaceEditor (ported from OpenManus)
│   │   ├── editor.py         #     view/create/str_replace/insert/undo_edit
│   │   ├── operator.py       #     LocalFileOperator (UTF-8, async)
│   │   └── safety.py         #     ensure_allowed() — shared path allowlist
│   ├── computer/             #   PowerShell shell tool
│   │   ├── shell.py          #     cwd uses file_editor's allowlist; UTF-8 preamble
│   │   ├── safety.py         #     deny/confirm classifier
│   │   └── output.py
│   ├── tavily_search/
│   └── rag/
│
├── session/                  # Conversation persistence
│   ├── manager.py, history.py, image.py, state.py, user.py, keys.py
│   └── cleanup.py            #   clear_history (preserves intimacy) + reset_all
│
├── messaging/, prompt/, llm/, net/, emotion/, vision/, memory_manage/
└── models.py                 # Shared request/response and prompt context models
```

## Layering Rules

- **Channel adapter** (`bot/`): translates Telegram updates into
  `InboundMessage` / `OutboundMessage` on the `MessageBus`. Does not call
  `AgentService` directly.
- **Service** (`core/agent_service.py`): one `_handle_message` per turn:
  prepares context (`prepare_agent_context`, history), loads any persisted
  `AgentTaskState`, delegates to the Flow, writes session history.
- **Flow** (`core/flow/`): orchestrates a turn end-to-end. Decides chat vs
  planning, owns step routing, handles `waiting_human` resume and approval.
  - `PlanningFlow` auto-advances every step (`while True`) in a single turn,
    exits when: plan complete / `waiting_human` / step failed / sub-agent
    called the `terminate` tool. Routes each step to an agent by
    `[AGENT_NAME]` marker in the step text — see ``plan_agents`` kwarg on
    ``AgentService``.
- **Agent** (`core/agent/`): generic ReAct-style step loop. Drives the LLM,
  executes tool_calls, owns OpenAI-protocol invariants (every assistant
  `tool_calls` is paired with a `tool` response).
- **Tools** (`core/tool/`): self-contained capabilities. Return
  `ToolResult` / `ToolFailure`; never raise out of `execute()` to the agent.

## Placement Rules

- Channel-specific code → `bot/`. Never in `core/`.
- New turn-level flow → `core/flow/<flow_name>.py`. Update `core/flow/__init__.py`.
- New agent variant → `core/agent/<name>_agent.py`, extending `ToolCallAgent` or `ChatAgent`.
- New tool with >1 file → `core/tool/<tool_name>/`. Single-file tools stay flat in `core/tool/`.
- New session field / persistence behavior → `core/session/`. Expose via
  `SessionManager`.
- Cross-channel message fields → `core/messaging/models.py`.
- HTTP endpoints → `llm/`. Bot-side LLM client → `core/llm/client.py`.

## Persistence Boundary

- **Redis**: per-conversation `AgentTaskState` (TTL = `SESSION_TTL`),
  history cache, image description cache, user state hash.
- **SQLite** (`db/`): durable users / conversations / memories tables.
- Falls back gracefully: redis outages return defaults but log a warning.

## Test Layout

- `tests/test_planning_flow_resume.py` — end-to-end through
  `AgentService.handle` (PlanningFlow resume, cancel, status, completion).
- `tests/test_planning_flow_routing.py` — `[AGENT_NAME]` step-type dispatch
  + `terminate` tool aborting the whole plan (OpenManus parity).
- `tests/test_file_editor.py` — StrReplaceEditor end-to-end (create/view/
  str_replace/insert/undo) + path allowlist checks.
- `tests/test_approval_reply.py` — parameterized reject/approve cases
  (regression for AUDIT P-01).
- `tests/test_shell_safety.py` — classify_command coverage + `_resolve_cwd`
  containment (regression for AUDIT T-01 / T-02).
- `tests/test_tool_collection.py` — ToolCollection lookup + error semantics
  (AUDIT T-05 / T-06 / T-07).
- `tests/test_session_redis_fallback.py` — session-layer redis-failure paths.

## Run

1. Start Redis
2. Start the LLM service: `python llm/api.py`
3. Start the bot: `python main.py`

## Notes

- Telegram traffic: `bot/telegram_channel.py`
- Model calls from the bot: `core/llm/client.py`
- LLM HTTP endpoints: `llm/api.py`
- Turn orchestration: `core/agent_service.py` → `core/flow/planning.py`
- Tool execution: `core/agent/toolcall.py` (via ChatAgent)
- Audit findings + change rationale: `AUDIT.md`
