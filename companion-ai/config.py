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

    # LLM 统一接入（OpenAI 兼容格式）
    # 本地 Ollama：保持默认值即可；外部 API：修改 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1/")
    LLM_API_KEY: str  = os.getenv("LLM_API_KEY",  "ollama")
    LLM_MODEL: str    = os.getenv("LLM_MODEL",    os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"))

    # Tools
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "3"))
    TOOL_SELECT_MODEL: str = os.getenv("TOOL_SELECT_MODEL", "qwen2.5:0.5b")
    TOOL_SELECT_TIMEOUT: float = float(os.getenv("TOOL_SELECT_TIMEOUT", "8.0"))

    # RAG
    OLLAMA_EMBED_URL: str = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "bge-m3")
    CHROMA_DIR: Path = BASE_DIR / "data" / "chroma"
    DOCS_DIR: Path = BASE_DIR / "docs"
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))        # ChromaDB 召回候选数
    RAG_EVIDENCE_TOP_N: int = int(os.getenv("RAG_EVIDENCE_TOP_N", "3"))  # 注入主模型的条数

    # Conversation
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))

    # Role
    DEFAULT_ROLE: str = os.getenv("DEFAULT_ROLE", "jiejie")
    ROLES_DIR: Path = BASE_DIR / "roles" / "personas"


config = Config()
