from __future__ import annotations

import asyncio
import base64
import logging

import yaml
from telegram import Update
from telegram.error import NetworkError, TimedOut
from collections.abc import Callable, Awaitable

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import config
from core.image_describer import describe_image
from core.message_bus import MessageBus
from core.messages import InboundMessage, OutboundMessage
from core.session_manager import SessionManager

logger = logging.getLogger(__name__)


class TelegramChannel:
    name = "telegram"

    def __init__(self, *, bus: MessageBus, session: SessionManager) -> None:
        self._bus = bus
        self._session = session
        self._bus.subscribe_outbound(self.name, self._on_outbound)

    def bind_bot(self, bot) -> None:
        self._bot = bot

    def build_application(
        self,
        *,
        post_init: Callable[[Application], Awaitable[None]] | None = None,
        post_shutdown: Callable[[Application], Awaitable[None]] | None = None,
    ) -> Application:
        if not config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

        builder = Application.builder().token(config.TELEGRAM_BOT_TOKEN)
        if post_init:
            builder = builder.post_init(post_init)
        if post_shutdown:
            builder = builder.post_shutdown(post_shutdown)
        app = builder.build()
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("reset", self.cmd_reset))
        app.add_handler(CommandHandler("me", self.cmd_me))
        app.add_handler(CommandHandler("profile", self.cmd_profile))
        app.add_handler(CommandHandler("roles", self.cmd_roles))
        app.add_handler(CommandHandler("switch", self.cmd_switch))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.on_photo))
        app.add_error_handler(self.on_error)
        return app

    async def _on_outbound(self, msg: OutboundMessage) -> None:
        # The Application bot is only available after build_application() starts.
        # The callback is bound through the bus, so the active bot is stored lazily.
        bot = getattr(self, "_bot", None)
        if bot is None:
            logger.warning("Telegram bot is not ready, dropping outbound message")
            return

        for attempt in range(3):
            try:
                await bot.send_message(
                    chat_id=msg.chat_id,
                    text=msg.content,
                    parse_mode="HTML",
                )
                return
            except Exception as exc:
                if attempt == 2:
                    logger.error(
                        "[telegram] send failed after 3 attempts chat_id=%s err=%s",
                        msg.chat_id,
                        exc,
                    )
                else:
                    logger.warning(
                        "[telegram] send attempt %s failed chat_id=%s err=%s",
                        attempt + 1,
                        msg.chat_id,
                        exc,
                    )
                    await asyncio.sleep(1)

    async def publish_user_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        content: str,
        media: list[str] | None = None,
    ) -> None:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return

        self._bot = context.bot
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        await self._bus.publish_inbound(
            InboundMessage(
                channel=self.name,
                sender=str(user.id),
                chat_id=str(chat.id),
                content=content,
                media=media or [],
                metadata={"username": user.username or user.first_name or ""},
            )
        )

    def _list_roles(self) -> list[str]:
        return [p.stem for p in config.ROLES_DIR.glob("*.yaml")]

    def _load_role(self, role_id: str) -> dict:
        path = config.ROLES_DIR / f"{role_id}.yaml"
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not update.message:
            return
        await self._session.ensure_user(user.id, user.username or user.first_name or "")
        name = user.first_name or "你好"
        await update.message.reply_text(
            f"{name}，我在。直接和我说话就行，也可以发图片给我。"
        )

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return
        await self._session.clear_history(update.effective_user.id)
        await update.message.reply_text("这段会话的短期上下文已经清空了。")

    async def cmd_me(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return
        if not context.args:
            await update.message.reply_text("用法：`/me 你的昵称`", parse_mode="Markdown")
            return
        nickname = " ".join(context.args)
        await self._session.set_nickname(update.effective_user.id, nickname)
        await update.message.reply_text(f"记住了，以后我会叫你 {nickname}。")

    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user = await self._session.get_user(user_id)
        intimacy = await self._session.get_intimacy(user_id)
        if not user:
            await update.message.reply_text(
                "你还没有初始化会话，先发 `/start`。", parse_mode="Markdown"
            )
            return
        nickname = user.get("nickname") or user.get("username") or "未设置"
        text = (
            f"角色：{user['role_id']}\n"
            f"昵称：{nickname}\n"
            f"亲密度：{intimacy}/100"
        )
        await update.message.reply_text(text)

    async def cmd_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        roles = self._list_roles()
        if not roles:
            await update.message.reply_text("当前没有可切换角色。")
            return
        await update.message.reply_text("可用角色：\n" + "\n".join(f"- {role}" for role in roles))

    async def cmd_switch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.message:
            return
        if not context.args:
            await update.message.reply_text(
                "用法：`/switch 角色ID`，可以先用 `/roles` 查看。",
                parse_mode="Markdown",
            )
            return

        role_id = context.args[0]
        if role_id not in self._list_roles():
            await update.message.reply_text(
                f"角色 `{role_id}` 不存在，先用 `/roles` 查看可选项。",
                parse_mode="Markdown",
            )
            return

        await self._session.set_role(update.effective_user.id, role_id)
        await self._session.clear_history(update.effective_user.id)
        role = self._load_role(role_id)
        greeting = role.get("greeting", f"已经切换到 {role_id}。")
        await update.message.reply_text(greeting)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        text = (
            "/start 初始化会话\n"
            "/me [昵称] 设置昵称\n"
            "/profile 查看当前资料\n"
            "/roles 查看角色列表\n"
            "/switch [角色ID] 切换角色\n"
            "/reset 清空短期上下文\n"
            "/help 查看帮助"
        )
        await update.message.reply_text(text)

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (update.message.text if update.message else "" or "").strip()
        if not text:
            return
        await self.publish_user_message(update, context, content=text)

    async def on_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.photo or not update.effective_user:
            return
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        user_message = (update.message.caption or "").strip() or "请看看这张图片。"

        await self.publish_user_message(
            update,
            context,
            content=user_message,
            media=[image_b64],
        )
        asyncio.create_task(
            self._save_image_desc_async(update.effective_user.id, image_b64)
        )

    async def _save_image_desc_async(self, user_id: int, image_b64: str):
        try:
            desc = await describe_image(image_b64)
            if desc:
                desc_text = f"""
场景：{desc.scene}
物体：{", ".join(desc.objects)}
文字：{", ".join(desc.text_ocr)}
用户相关信息：{", ".join(desc.user_relevant_fact)}""".strip()
                await self._session.set_last_image_desc(user_id, desc_text)
                logger.info("[%s] image desc saved: %s", user_id, desc_text)
        except Exception as exc:
            logger.error("[%s] async image desc failed: %s", user_id, exc)

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        if isinstance(error, (NetworkError, TimedOut)):
            logger.warning("Telegram network error: %s", error)
            return
        logger.exception("Unhandled Telegram update error", exc_info=error)
