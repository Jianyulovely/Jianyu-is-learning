import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")


def _provider_value(name: str, default: str = "") -> str:
    """根据模型服务商获取 env 中对应的 url 和 key"""
    prefix = LLM_PROVIDER.upper()
    return os.getenv(f"{prefix}_{name}", default)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_optional_float(name: str, default: float | None = None) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return float(value)


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
    LLM_MODEL: str = _provider_value("MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"))
    LLM_BASE_URL: str = _provider_value("URL", "http://localhost:11434/v1/")
    LLM_API_KEY: str = _provider_value("API_KEY", "ollama")
    OLLAMA_MODEL: str = LLM_MODEL
    OLLAMA_GEN_URL: str = os.getenv("OLLAMA_GEN_URL", "http://localhost:11434/api/generate")
    LLM_TEMPERATURE: float | None = _env_optional_float("LLM_TEMPERATURE", 0.85)
    LLM_TOP_P: float | None = _env_optional_float("LLM_TOP_P", 0.9)
    LLM_SEND_SAMPLING_PARAMS: bool = _env_bool("LLM_SEND_SAMPLING_PARAMS", False)

    # Tools
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_URL = "https://api.tavily.com/search"
    # 工具调用轮数：chat 模式短链路；planning 在每个 step 内独立计数，故可适当放宽。
    MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "4"))
    MAX_TOOL_ROUNDS_PLANNING: int = int(os.getenv("MAX_TOOL_ROUNDS_PLANNING", "8"))
    # 是否向上游 LLM API 透传 parallel_tool_calls=False 标志。Ollama OpenAI 兼容接口
    # 可能不识别此参数，必要时关闭。
    LLM_SUPPORTS_PARALLEL_TOOL_CALLS_FLAG: bool = _env_bool(
        "LLM_SUPPORTS_PARALLEL_TOOL_CALLS_FLAG", True
    )

    # RAG
    OLLAMA_EMBED_URL: str = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embed")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "bge-m3")
    CHROMA_DIR: Path = BASE_DIR / "data" / "chroma"
    DOCS_DIR: Path = BASE_DIR / "docs"
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_EVIDENCE_TOP_N: int = int(os.getenv("RAG_EVIDENCE_TOP_N", "3"))

    # Conversation
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))
    MAX_HISTORY_MSGS: int = int(os.getenv("MAX_HISTORY_MSGS", "24"))
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "7200"))
    INTIMACY_INIT: int = int(os.getenv("INTIMACY_INIT", "20"))

    # Role
    DEFAULT_ROLE: str = os.getenv("DEFAULT_ROLE", "jiejie")
    ROLES_DIR: Path = BASE_DIR / "roles" / "personas"

    # 用户所在时区
    USER_TIMEZONE: str = "Asia/Shanghai"


config = Config()
