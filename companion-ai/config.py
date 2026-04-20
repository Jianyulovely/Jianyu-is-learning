import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_USER_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
    ]

    # LLM service
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:8000")

    # Ollama
    OLLAMA_GEN_URL: str = os.getenv("OLLAMA_GEN_URL", "http://localhost:11434/api/generate")
    OLLAMA_CHAT_URL: str = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

    # Tools
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "3"))

    # Conversation
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))

    # Role
    DEFAULT_ROLE: str = os.getenv("DEFAULT_ROLE", "jiejie")
    ROLES_DIR: Path = BASE_DIR / "roles" / "personas"


config = Config()
