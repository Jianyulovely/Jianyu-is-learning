"""
Compatibility layer for older imports.

The current Telegram entrypoint lives in `bot/telegram_channel.py` and is wired
from `main.py`.
"""

from bot.telegram_channel import TelegramChannel
from core.agent_service import AgentService
from core.messaging.bus import MessageBus
from core.session.manager import SessionManager


def build_application():
    bus = MessageBus()
    session = SessionManager()
    _ = AgentService(session=session)
    return TelegramChannel(bus=bus, session=session).build_application()
