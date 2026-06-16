import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
def _provider_value(name: str, default: str = "") -> str:
    """根据模型服务商获取env中对应的url 和 key"""                                                              
    prefix = LLM_PROVIDER.upper()                                                                                                
    return os.getenv(f"{prefix}_{name}", default)

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_USER_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
    ]

    # LLM service
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:8000")

    # LLM 统一接入（OpenAI 兼容格式）
    # 本地 Ollama：保持默认值即可；外部 API：修改 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
    LLM_MODEL: str    = _provider_value("MODEL",    os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"))
    LLM_BASE_URL: str = _provider_value("URL", "http://localhost:11434/v1/")
    LLM_API_KEY: str  = _provider_value("API_KEY",  "ollama")

    # Tools
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_URL = "https://api.tavily.com/search"
    MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "3"))
    
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

    # 用户所在时区
    USER_TIMEZONE: str = "Asia/Shanghai"


config = Config()
