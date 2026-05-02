import asyncio
import base64
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

import yaml
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import config
from core.emotion_detector import detect as detect_emotion
from core.formatter import format_reply
import core.http_client as http_client
from core.http_client import safe_post
from core.memory_service import MemoryService
from core.prompt_engine import PromptEngine
from core.session_manager import SessionManager
from core.tools import execute_tool, select_tools
from db.models import init_db
from rag.indexer import scan_and_index

logger = logging.getLogger(__name__)

_session = SessionManager()
_memory_service = MemoryService()
_prompt_engine = PromptEngine()


def _list_roles() -> list[str]:
    return [p.stem for p in config.ROLES_DIR.glob("*.yaml")]


def _load_role(role_id: str) -> dict:
    path = config.ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def _describe_image(image_b64: str) -> str:
    payload = {
        "system_prompt": "请用简洁中文描述这张图片里最重要的内容，重点关注人物、场景、动作和明显文字。",
        "user_message": "请描述这张图片。",
        "images": [image_b64],
        "context": [],
        "max_new_tokens": 80,
        "temperature": 0.3,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    }
    resp = await safe_post(f"{config.LLM_API_URL}/generate", json=payload, timeout=60.0)
    resp.raise_for_status()
    return (resp.json().get("reply") or "").strip()


async def _execute_selected_tools(tools: list[dict], user_message: str) -> str:
    if not tools:
        return ""

    results = await asyncio.gather(
        *[execute_tool(tool["function"]["name"], {"query": user_message}) for tool in tools]
    )
    parts: list[str] = []
    for tool, result in zip(tools, results):
        name = tool["function"]["name"]
        preview = (result or "")[:200]
        logger.info("[tool_exec] %s result preview: %r", name, preview)
        parts.append(f"[{name}]\n{result}")
    context = "\n\n".join(parts)
    logger.info("[tool_context] total_len=%s", len(context))
    return context


async def _call_llm(
    system_prompt: str,
    messages: list[dict],
    images: list[str] | None = None,
    tool_context: str = "",
) -> str:
    effective_messages = list(messages)
    images = images or []

    if tool_context:
        system_prompt = (
            system_prompt
            + "\n\n以下是工具返回的外部信息。仅在相关时引用，不要生硬照搬，也不要编造成你亲自经历过。"
        )
        if effective_messages and effective_messages[-1]["role"] == "user":
            last = effective_messages[-1]
            effective_messages[-1] = {
                **last,
                "content": f"[工具上下文]\n{tool_context}\n\n---\n{last['content']}",
            }
        else:
            effective_messages.append({"role": "user", "content": f"[工具上下文]\n{tool_context}"})

    payload = {
        "system_prompt": system_prompt,
        "messages": effective_messages,
        "images": images,
        "temperature": 0.85,
        "top_p": 0.9,
    }
    resp = await safe_post(f"{config.LLM_API_URL}/chat", json=payload)
    if resp.status_code >= 400:
        logger.error("LLM /chat failed: %s %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json().get("reply", "")


def _post_process(reply: str, role: dict) -> str:
    for phrase in role.get("forbidden_phrases", []):
        if phrase and phrase in reply:
            logger.warning("Forbidden phrase detected, using fallback.")
            return "我换一种更自然的说法继续和你聊。"
    return reply


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or ""

    await _session.ensure_user(user_id, username)
    name = user.first_name or "你"
    await update.message.reply_text(f"{name}，我在。直接和我说话就行，也可以发图片给我。")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _session.clear_history(user_id)
    await update.message.reply_text("这段会话的短期上下文已经清空了。")


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("用法：`/me 你的昵称`", parse_mode="Markdown")
        return
    nickname = " ".join(args)
    await _session.set_nickname(user_id, nickname)
    await update.message.reply_text(f"记住了，以后我会叫你 {nickname}。")


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await _session.get_user(user_id)
    intimacy = await _session.get_intimacy(user_id)
    if not user:
        await update.message.reply_text("你还没有初始化会话，先发 `/start`。", parse_mode="Markdown")
        return
    nickname = user.get("nickname") or user.get("username") or "未设置"
    text = (
        f"角色：{user['role_id']}\n"
        f"昵称：{nickname}\n"
        f"亲密度：{intimacy}/100"
    )
    await update.message.reply_text(text)


async def cmd_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roles = _list_roles()
    if not roles:
        await update.message.reply_text("当前没有可切换角色。")
        return
    await update.message.reply_text("可用角色：\n" + "\n".join(f"- {role}" for role in roles))


async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("用法：`/switch 角色ID`，可以先用 `/roles` 查看。", parse_mode="Markdown")
        return

    role_id = args[0]
    if role_id not in _list_roles():
        await update.message.reply_text(f"角色 `{role_id}` 不存在，先用 `/roles` 查看可选项。", parse_mode="Markdown")
        return

    await _session.set_role(user_id, role_id)
    await _session.clear_history(user_id)
    role = _load_role(role_id)
    greeting = role.get("greeting", f"已经切换到 {role_id}。")
    await update.message.reply_text(greeting)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def _handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str,
    images: list[str] | None = None,
):
    user = update.effective_user
    user_id = user.id
    images = images or []
    timezone_name = "Asia/Shanghai"
    current_time_iso = datetime.now(ZoneInfo(timezone_name)).isoformat()

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await _session.ensure_user(user_id, user.username or user.first_name or "")

    emotion = detect_emotion(user_message)
    logger.info("[%s] user: %r emotion: %s", user_id, user_message, emotion.tag)

    intimacy = await _session.get_intimacy(user_id)
    db_user = await _session.get_user(user_id)
    user_name = (db_user or {}).get("nickname") or user.first_name or "用户"
    role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
    role = _load_role(role_id)

    await _session.append_message(user_id, "user", user_message, emotion.tag)

    prompt_image_context = ""
    if not images:
        prompt_image_context = await _session.get_last_image_desc(user_id)

    memory_summary = await _memory_service.build_memory_summary(
        user_id=user_id,
        current_message=user_message,
        current_time_iso=current_time_iso,
        timezone_name=timezone_name,
    )

    system_prompt = _prompt_engine.build_system_prompt(
        role_id=role_id,
        user_name=user_name,
        emotion=emotion,
        intimacy_level=intimacy,
        image_context=prompt_image_context,
        memory_summary=memory_summary,
        current_time_iso=current_time_iso,
        timezone_name=timezone_name,
    )

    tools_schemas, history = await asyncio.gather(
        select_tools(user_message),
        _session.get_history(user_id),
    )
    tool_context = await _execute_selected_tools(tools_schemas, user_message)

    try:
        reply = await _call_llm(
            system_prompt=system_prompt,
            messages=history,
            images=images,
            tool_context=tool_context,
        )
        reply = _post_process(reply, role)
        reply = format_reply(reply)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        reply = "我这边刚才有点卡住了，你可以再发一次，我继续接。"

    if not reply.strip():
        logger.warning("[%s] empty reply from LLM, raw: %r", user_id, reply)
        reply = "我刚才没组织好这句，你再说一句，我接着陪你聊。"

    logger.info("[%s] bot (%s): %r", user_id, role_id, reply)

    await _session.append_message(user_id, "assistant", reply)
    await _session.bump_intimacy(user_id, emotion.tag)
    await _session.update_state(user_id, emotion_tag=emotion.tag)

    asyncio.create_task(
        _memory_service.after_turn(
            user_id=user_id,
            user_message=user_message,
            assistant_reply=reply,
            image_context="",
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
    )

    for attempt in range(3):
        try:
            await update.message.reply_text(reply, parse_mode="HTML")
            break
        except Exception as exc:
            if attempt == 2:
                logger.error("[%s] send failed after 3 attempts: %s", user_id, exc)
            else:
                logger.warning("[%s] send attempt %s failed, retrying: %s", user_id, attempt + 1, exc)
                await asyncio.sleep(1)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return
    await _handle_message(update, context, user_message=text)


async def _save_image_desc_async(user_id: int, image_b64: str):
    try:
        desc = await _describe_image(image_b64)
        if desc:
            await _session.set_last_image_desc(user_id, desc)
            logger.info("[%s] image desc saved: %s", user_id, desc)
    except Exception as exc:
        logger.error("[%s] async image desc failed: %s", user_id, exc)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    user_message = (update.message.caption or "").strip() or "请看看这张图片。"

    await _handle_message(update, context, user_message=user_message, images=[image_b64])
    asyncio.create_task(_save_image_desc_async(user_id, image_b64))


async def on_startup(app: Application):
    await init_db()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, scan_and_index)
    logger.info("Startup complete.")


async def on_shutdown(app: Application):
    await http_client.aclose()
    logger.info("HTTP client closed.")


def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("roles", cmd_roles))
    app.add_handler(CommandHandler("switch", cmd_switch))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    return app
