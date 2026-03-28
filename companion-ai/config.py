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

    # Model
    MODEL_PATH: str = os.getenv(
        "MODEL_PATH",
        str(BASE_DIR.parent / "models/qwen/Qwen2.5-0.5B-Instruct"),
    )
    CUDA_DEVICE: str = os.getenv("CUDA_DEVICE", "cuda:0")

    # Conversation
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))

    # Role
    DEFAULT_ROLE: str = os.getenv("DEFAULT_ROLE", "jiejie")
    ROLES_DIR: Path = BASE_DIR / "roles" / "personas"


config = Config()
