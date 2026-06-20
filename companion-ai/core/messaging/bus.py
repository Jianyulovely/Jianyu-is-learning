from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from core.messaging.models import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

OutboundCallback = Callable[[OutboundMessage], Awaitable[None]]


class MessageBus:
    def __init__(self) -> None:
        self._inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._subscribers: dict[str, list[OutboundCallback]] = {}
        self._running = False

    async def publish_inbound(self, msg: InboundMessage) -> None:
        await self._inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        return await self._inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        await self._outbound.put(msg)

    def subscribe_outbound(self, channel: str, callback: OutboundCallback) -> None:
        """订阅出栈消息"""
        self._subscribers.setdefault(channel, []).append(callback)

    async def dispatch_outbound(self) -> None:
        """将智能体的回复分发给对应渠道的订阅者"""
        self._running = True
        while self._running:
            try:
                msg = await asyncio.wait_for(self._outbound.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            for callback in self._subscribers.get(msg.channel, []):
                try:
                    await callback(msg)
                except Exception as first_err:
                    logger.warning(
                        "Outbound dispatch failed, retrying channel=%s chat_id=%s err=%s",
                        msg.channel,
                        msg.chat_id,
                        first_err,
                    )
                    await asyncio.sleep(2)
                    try:
                        await callback(msg)
                    except Exception as second_err:
                        logger.error(
                            "Outbound dispatch failed after retry channel=%s chat_id=%s err=%s",
                            msg.channel,
                            msg.chat_id,
                            second_err,
                        )

    def stop(self) -> None:
        self._running = False

    @property
    def inbound_size(self) -> int:
        return self._inbound.qsize()

    @property
    def outbound_size(self) -> int:
        return self._outbound.qsize()
