# Companion AI

Telegram bot + LLM service + local memory/tooling.

## Layout

- `main.py`: bot entrypoint
- `bot/`: Telegram channel adapter
- `core/`: agent, session, prompt, memory, tools, messaging
- `llm/`: local LLM API wrapper
- `db/`: SQLite / Redis helpers
- `roles/`: persona configs
- `data/`: local database and indexes

## Run

1. Start Redis
2. Start `llm/api.py`
3. Start `main.py`

## Notes

- Telegram traffic is handled in `bot/telegram_channel.py`
- Model calls are handled in `core/llm_client.py`
- Turn orchestration is handled in `core/agent_service.py`
