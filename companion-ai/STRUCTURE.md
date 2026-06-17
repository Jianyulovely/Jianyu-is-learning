# Companion AI Structure

This project is split by feature ownership. Keep entrypoints thin, keep shared contracts explicit, and avoid placing new feature code directly in `core/`.

## Top-Level Directories

- `main.py`: Telegram bot runtime entrypoint. It wires the bus, session manager, agent service, database initialization, and startup/shutdown tasks.
- `bot/`: Channel adapter layer. Telegram-specific commands, update parsing, and outbound delivery live here.
- `core/`: Product and application logic. Code here should not depend on Telegram-specific types.
- `llm/`: FastAPI service that exposes local model endpoints such as `/chat`, `/generate`, and `/health`.
- `db/`: Persistence adapters for SQLite and Redis.
- `roles/`: Persona YAML files.
- `data/`: Local runtime data such as SQLite databases and vector indexes. This should stay out of source control.

## Core Feature Groups

- `core/agent_service.py`: High-level agent turn orchestration. It coordinates session, prompt, memory, LLM calls, tool execution, and final reply persistence.
- `core/agent/`: Agent internals that support `AgentService`, including context preparation, task state, task storage, helper functions, and reply formatting.
- `core/session/`: Conversation session operations. Put user profile, history, state, image cache, keys, and cleanup logic here.
- `core/messaging/`: Channel-independent message models and the async message bus.
- `core/prompt/`: System prompt construction.
- `core/memory_manage/`: Memory extraction, summarization, saving, retrieval, and memory data models.
- `core/tool/`: Tool framework and concrete tools. Each complex tool can own a subdirectory, such as `rag/` or `tavily_search/`.
- `core/llm/`: Bot-side client for the LLM service. This is not the FastAPI service itself.
- `core/net/`: Shared network helpers such as the reusable HTTP client.
- `core/vision/`: Image understanding helpers.
- `core/emotion/`: Emotion detection.
- `core/models.py`: Shared request/response and prompt context models used across multiple core areas.

## Placement Rules

- Add channel-specific code to `bot/`, not `core/`.
- Add orchestration flow changes to `core/agent_service.py` only when they coordinate multiple subsystems.
- Add isolated agent helper logic to `core/agent/` instead of growing `agent_service.py`.
- Add new user/session persistence behavior to `core/session/`, with `SessionManager` exposing the public method.
- Add cross-channel message fields to `core/messaging/models.py`.
- Add a new tool under `core/tool/<tool_name>/` when it has more than one file; keep simple tools as one file under `core/tool/`.
- Add LLM provider or request-shaping logic to `core/llm/`; add HTTP endpoints to `llm/`.
- Keep runtime files under `data/` and caches under `__pycache__/`; do not commit them.

## Current Cleanup Targets

- Finish moving tracked legacy modules from `core/*.py` to their new feature directories. The old names include `emotion_detector.py`, `formatter.py`, `http_client.py`, `image_describer.py`, `llm_client.py`, `message_bus.py`, `messages.py`, `prompt_engine.py`, `session_manager.py`, and `tools.py`.
- Keep imports pointed at the new paths, for example `core.llm.client`, `core.messaging.bus`, `core.messaging.models`, `core.session.manager`, and `core.net.http`.
- Review mojibake text in source files. Several Chinese comments and user-facing strings appear encoded incorrectly even though the code still compiles.
