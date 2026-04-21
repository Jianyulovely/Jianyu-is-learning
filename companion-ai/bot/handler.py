"""
Telegram Bot Handler —— P1
职责：接收消息 → SessionManager 加载上下文 → EmotionDetector 分析情绪
      → PromptEngine 组装请求 → 调用 LLM API → PostProcess → 回复用户
"""
import asyncio
import base64
import logging

import httpx
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
from core.http_client import safe_post
import core.http_client as http_client
from core.prompt_engine import PromptEngine
from core.session_manager import SessionManager
from core.tools import execute_tool, select_tools
from db.models import init_db
from rag.indexer import scan_and_index

logger = logging.getLogger(__name__)

_session = SessionManager()
_prompt_engine = PromptEngine()


def _list_roles() -> list[str]:
    return [p.stem for p in config.ROLES_DIR.glob("*.yaml")]


def _load_role(role_id: str) -> dict:
    path = config.ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── LLM API 调用 ──────────────────────────────────────────────────────────────

async def _describe_image(image_b64: str) -> str:
    """静默调用：让模型描述图片内容，结果不展示给用户。"""
    payload = {
        "system_prompt": "你是一个图像内容分析助手。用简短客观的一两句话描述图片内容，只描述事实，不加情感或评价。",
        "user_message": "描述这张图片的内容",
        "images": [image_b64],
        # 防止污染上下文
        "context": [],
        "max_new_tokens": 80,
        "temperature": 0.3,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    }
    resp = await safe_post(f"{config.LLM_API_URL}/generate", json=payload, timeout=60.0)
    resp.raise_for_status()
    return resp.json()["reply"].strip()


async def _execute_selected_tools(tools: list[dict], user_message: str) -> str:
    """预执行小模型选出的工具，并发调用后拼接为证据字符串。"""
    if not tools:
        return ""
    results = await asyncio.gather(*[
        execute_tool(t["function"]["name"], {"query": user_message})
        for t in tools
    ])
    parts = []
    for tool, result in zip(tools, results):
        name = tool["function"]["name"]
        logger.info(f"[tool_exec] {name} result preview: {result[:200]!r}")
        parts.append(f"[{name}]\n{result}")
    context = "\n\n".join(parts)
    logger.info(f"[tool_context] total_len={len(context)}")
    return context


async def _call_llm(
    system_prompt: str,
    messages: list[dict],
    images: list[str] = [],
    tool_context: str = "",
) -> str:
    effective_messages = list(messages)

    if tool_context:
        system_prompt = system_prompt + "\n\n请优先基于[参考资料]回答，不要凭空猜测。"
        if effective_messages and effective_messages[-1]["role"] == "user":
            last = effective_messages[-1]
            effective_messages[-1] = {
                **last,
                "content": f"[参考资料]\n{tool_context}\n\n---\n{last['content']}",
            }
        else:
            effective_messages.append({"role": "user", "content": f"[参考资料]\n{tool_context}"})

    payload = {
        "system_prompt": system_prompt,
        "messages": effective_messages,
        "images": images,
        "temperature": 0.85,
        "top_p": 0.9,
    }
    resp = await safe_post(f"{config.LLM_API_URL}/chat", json=payload)
    resp.raise_for_status()
    return resp.json().get("reply", "")


# 对于llm返回内容，根据违禁词表进行过滤
def _post_process(reply: str, role: dict) -> str:
    for phrase in role.get("forbidden_phrases", []):
        if phrase in reply:
            logger.warning("Forbidden phrase detected, using fallback.")
            return "嗯……有点走神了，你刚才说什么来着？"
    return reply


# ── 指令处理 ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or ""

    await _session.ensure_user(user_id, username)
    name = user.first_name or "你"
    await update.message.reply_text(
        f"嗨，{name}～ 如果有什么想聊的话，直接说就好。"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await _session.clear_history(user_id)
    await update.message.reply_text("好，我们重新开始聊吧～")


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("用法：/me 你的昵称")
        return
    nickname = " ".join(args)
    await _session.set_nickname(user_id, nickname)
    await update.message.reply_text(f"好，我以后叫你{nickname}～")


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await _session.get_user(user_id)
    intimacy = await _session.get_intimacy(user_id)
    if not user:
        await update.message.reply_text("还没注册，先发 /start 吧～")
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
    await update.message.reply_text("可用角色：\n" + "\n".join(f"• {r}" for r in roles))


async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("用法：/switch <角色ID>，用 /roles 查看可用角色")
        return
    role_id = args[0]
    if role_id not in _list_roles():
        await update.message.reply_text(f"角色 '{role_id}' 不存在，用 /roles 查看可用角色")
        return
    await _session.set_role(user_id, role_id)
    await _session.clear_history(user_id)
    role = _load_role(role_id)
    greeting = role.get("greeting", "嗨～换新角色了，有什么想聊的吗？")
    await update.message.reply_text(greeting)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/start           —  开始对话\n"
        "/me [昵称]       —  设置你的昵称\n"
        "/profile         —  查看角色与亲密度\n"
        "/roles           —  查看可用角色\n"
        "/switch [角色ID] —  切换角色\n"
        "/reset           —  清除当前会话\n"
        "/help            —  查看指令列表"
    )
    await update.message.reply_text(text)


# ── 普通消息处理 ──────────────────────────────────────────────────────────────

async def _handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str,
    images: list[str] = [],
):
    """文字和图片消息的公共处理逻辑。"""
    user = update.effective_user
    user_id = user.id

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    await _session.ensure_user(user_id, user.username or user.first_name or "")

    emotion = detect_emotion(user_message)
    logger.info(f"[{user_id}] user: {user_message!r}  emotion: {emotion.tag}")

    intimacy = await _session.get_intimacy(user_id)
    db_user = await _session.get_user(user_id)
    user_name = (db_user or {}).get("nickname") or user.first_name or "你"
    role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
    role = _load_role(role_id)

    await _session.append_message(user_id, "user", user_message, emotion.tag)

    system_prompt = _prompt_engine.build_system_prompt(
        role_id=role_id,
        user_name=user_name,
        emotion=emotion,
        intimacy_level=intimacy,
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
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        reply = "哎，好像有点问题，稍等一下再试试？"

    if not reply.strip():
        logger.warning(f"[{user_id}] empty reply from LLM, raw: {repr(reply)}")
        reply = "嗯……刚才走神了，你再说一遍？"

    logger.info(f"[{user_id}] bot ({role_id}): {reply!r}")

    await _session.append_message(user_id, "assistant", reply)
    await _session.bump_intimacy(user_id, emotion.tag)
    await _session.update_state(user_id, emotion_tag=emotion.tag)

    for attempt in range(3):
        try:
            await update.message.reply_text(reply, parse_mode="HTML")
            break
        except Exception as e:
            if attempt == 2:
                logger.error(f"[{user_id}] send failed after 3 attempts: {e}")
            else:
                logger.warning(f"[{user_id}] send attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    await _handle_message(update, context, user_message=text)


async def _save_image_desc_async(user_id: int, image_b64: str):
    """后台任务：静默描述图片并写入记忆，不阻塞用户响应。"""
    try:
        desc = await _describe_image(image_b64)
        if desc:
            await _session.set_last_image_desc(user_id, desc)
            await _session.save_image_memory(user_id, desc)
            logger.info(f"[{user_id}] image desc saved: {desc}")
    except Exception as e:
        logger.error(f"[{user_id}] async image desc failed: {e}")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    user_message = (update.message.caption or "").strip() or "你看这张图"

    # 单次推理：图片和文字一起传给模型
    await _handle_message(update, context, user_message=user_message, images=[image_b64])

    # 后台异步：存图片描述到记忆，不阻塞
    asyncio.create_task(_save_image_desc_async(user_id, image_b64))


# ── 构建 Application ──────────────────────────────────────────────────────────

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

    # 用于用户在对话框中输入指令进行响应
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
