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

from bot.cli_channel import CLIChannel
import core.net.http as http_client
from bot.telegram_channel import TelegramChannel
from core.agent_service import AgentService
from core.messaging.bus import MessageBus
from core.messaging.models import InboundMessage, OutboundMessage
from core.session.manager import SessionManager
from db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class Runtime:
    """
    应用程序运行时容器，管理核心组件的生命周期。

    包含三个核心组件：
    - bus: 消息总线，负责渠道与智能体之间的消息传递
    - session: 会话管理器，管理用户会话和历史记录
    - agent: 智能体服务，协调 LLM、工具和对话流程
    """
    def __init__(self) -> None:
        self.bus = MessageBus()
        self.session = SessionManager()
        self.agent = AgentService(session=self.session)


async def _agent_worker(bus: MessageBus, agent: AgentService) -> None:
    """智能体处理消息队列"""
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


async def _start_runtime(runtime: Runtime) -> list[asyncio.Task]:
    """初始化
    启动后台任务：
       - _agent_worker: 消费入站消息，调用智能体处理
       - dispatch_outbound: 分发出站消息到各频道"""
    await init_db()
    await _scan_rag_index()
    return [
        asyncio.create_task(_agent_worker(runtime.bus, runtime.agent)),
        asyncio.create_task(runtime.bus.dispatch_outbound()),
    ]


async def _stop_runtime(runtime: Runtime, tasks: list[asyncio.Task]) -> None:
    runtime.bus.stop()
    for task in tasks:
        if task and not task.done():
            task.cancel()
    await asyncio.gather(*(task for task in tasks if task), return_exceptions=True)
    await http_client.aclose()


def build_application() -> Application:
    runtime = Runtime()
    channel = TelegramChannel(bus=runtime.bus, session=runtime.session)

    async def on_startup(app: Application) -> None:
        channel.bind_bot(app.bot)
        app.bot_data["runtime"] = runtime
        app.bot_data["runtime_tasks"] = await _start_runtime(runtime)
        logger.info("Startup complete.")

    async def on_shutdown(app: Application) -> None:
        await _stop_runtime(
            app.bot_data["runtime"],
            app.bot_data.get("runtime_tasks", []),
        )
        logger.info("HTTP client closed.")

    return channel.build_application(
        post_init=on_startup,
        post_shutdown=on_shutdown,
    )


async def run_cli() -> None:
    runtime = Runtime()
    channel = CLIChannel(bus=runtime.bus, session=runtime.session)
    tasks = await _start_runtime(runtime)
    logger.info("CLI started.")
    try:
        await channel.run()
    finally:
        await _stop_runtime(runtime, tasks)
        logger.info("CLI stopped.")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "cli":
        logger.info("Starting Companion AI CLI ...")
        asyncio.run(run_cli())
        return

    if mode != "tg":
        print("Usage: python main.py [cli|tg]")
        return

    logger.info("Starting Companion AI Bot ...")
    app = build_application()
    logger.info("Bot polling started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
