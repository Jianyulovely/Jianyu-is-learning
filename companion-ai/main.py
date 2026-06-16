"""
Companion AI - bot entrypoint.

Start the LLM service first:
    python llm/api.py
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application

import core.http_client as http_client
from bot.telegram_channel import TelegramChannel
from core.agent_service import AgentService
from core.message_bus import MessageBus
from core.messages import InboundMessage
from core.session_manager import SessionManager
from db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def _agent_worker(bus: MessageBus, agent: AgentService) -> None:
    while True:
        inbound: InboundMessage = await bus.consume_inbound()
        outbound = await agent.handle(inbound)
        await bus.publish_outbound(outbound)


async def _scan_rag_index() -> None:
    try:
        from core.tool.rag.indexer import scan_and_index
    except Exception as exc:
        logger.warning("RAG indexer is unavailable, skipping scan: %s", exc)
        return

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, scan_and_index)
    except Exception as exc:
        logger.warning("RAG index scan failed, continuing startup: %s", exc)


def build_application() -> Application:
    bus = MessageBus()
    session = SessionManager()
    agent = AgentService(session=session)
    channel = TelegramChannel(bus=bus, session=session)

    async def on_startup(app: Application) -> None:
        channel.bind_bot(app.bot)
        await init_db()
        await _scan_rag_index()
        app.bot_data["bus"] = bus
        app.bot_data["agent_worker_task"] = asyncio.create_task(
            _agent_worker(bus, agent)
        )
        app.bot_data["outbound_dispatch_task"] = asyncio.create_task(
            bus.dispatch_outbound()
        )
        logger.info("Startup complete.")

    async def on_shutdown(app: Application) -> None:
        bus.stop()
        tasks = [
            app.bot_data.get("agent_worker_task"),
            app.bot_data.get("outbound_dispatch_task"),
        ]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        await asyncio.gather(
            *(task for task in tasks if task),
            return_exceptions=True,
        )
        await http_client.aclose()
        logger.info("HTTP client closed.")

    return channel.build_application(
        post_init=on_startup,
        post_shutdown=on_shutdown,
    )


def main() -> None:
    logger.info("Starting Companion AI Bot ...")
    app = build_application()
    logger.info("Bot polling started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
