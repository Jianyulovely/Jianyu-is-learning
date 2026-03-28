"""
Companion AI —— Bot 入口
启动前请确保 LLM 服务已在 localhost:8000 运行：
    python llm/api.py
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.handler import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Companion AI Bot (P0 MVP)...")
    app = build_application()
    logger.info("Bot polling started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
