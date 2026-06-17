# Companion AI

Telegram bot + LLM service + local memory/tooling.

## Layout

- `main.py`: bot entrypoint
- `bot/`: Telegram channel adapter and command handlers
- `core/`: application logic, grouped by feature
- `core/agent_service.py`: turn orchestration and tool loop
- `core/agent/`: agent context, task state, task persistence, reply formatting helpers
- `core/session/`: user profile, history, state, image cache, and cleanup operations
- `core/messaging/`: inbound/outbound message contracts and async bus
- `core/prompt/`: system prompt assembly
- `core/memory_manage/`: memory extraction, summary, saving, and query service
- `core/tool/`: tool contracts, tool collection, Tavily search, RAG, human handoff, terminate
- `core/llm/`: bot-side LLM client for calling the local LLM service
- `core/net/`: shared HTTP client helpers
- `core/vision/`: image description
- `core/emotion/`: emotion detection
- `llm/`: FastAPI LLM service API
- `db/`: SQLite / Redis helpers
- `roles/`: persona configs
- `data/`: local database and indexes
- `STRUCTURE.md`: project structure rules

## Run

1. Start Redis
2. Start the LLM service: `python llm/api.py`
3. Start the bot: `python main.py`

## Notes

- Telegram traffic is handled in `bot/telegram_channel.py`
- Model calls from the bot are handled in `core/llm/client.py`
- LLM HTTP endpoints are handled in `llm/api.py`
- Turn orchestration is handled in `core/agent_service.py`
- New modules should follow the rules in `STRUCTURE.md`.
