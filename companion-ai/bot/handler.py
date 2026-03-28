"""
Telegram Bot Handler —— P1
职责：接收消息 → SessionManager 加载上下文 → EmotionDetector 分析情绪
      → PromptEngine 组装请求 → 调用 LLM API → PostProcess → 回复用户
"""
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
from core.prompt_engine import PromptEngine
from core.session_manager import SessionManager
from db.models import init_db

logger = logging.getLogger(__name__)

_session = SessionManager()
_prompt_engine = PromptEngine()


def _load_role(role_id: str) -> dict:
    path = config.ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── LLM API 调用 ──────────────────────────────────────────────────────────────

async def _call_llm(system_prompt: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": system_prompt}] + history
    payload = {
        "messages": messages,
        "max_new_tokens": 200,
        "temperature": 0.85,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{config.LLM_API_URL}/chat",
            json=payload,
            headers={"Connection": "close"},  # ⚠ 禁用连接复用，防止 SSH 隧道 502
        )
        resp.raise_for_status()
        return resp.json()["reply"]


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
        f"嗨，{name}～我是惠惠。有什么想聊的嘛，直接说就好。"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    r = __import__("db.redis_client", fromlist=["get_redis"]).get_redis()
    await r.delete(f"session:{user_id}:history")
    await r.delete(f"session:{user_id}:state")
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


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/start      —  开始对话\n"
        "/me [昵称]  —  设置你的昵称\n"
        "/profile    —  查看角色与亲密度\n"
        "/reset      —  清除当前会话\n"
        "/help       —  查看指令列表"
    )
    await update.message.reply_text(text)


# ── 普通消息处理 ──────────────────────────────────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()
    if not text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 确保用户存在
    await _session.ensure_user(user_id, user.username or user.first_name or "")

    # 情绪检测
    emotion = detect_emotion(text)

    # 加载历史 & 状态
    history = await _session.get_history(user_id)
    intimacy = await _session.get_intimacy(user_id)
    db_user = await _session.get_user(user_id)
    user_name = (db_user or {}).get("nickname") or user.first_name or "你"
    role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
    role = _load_role(role_id)

    # 追加用户消息到历史
    await _session.append_message(user_id, "user", text, emotion.tag)
    history = await _session.get_history(user_id)

    # 组装 system prompt
    system_prompt = _prompt_engine.build_system_prompt(
        role_id=role_id,
        user_name=user_name,
        emotion=emotion,
        intimacy_level=intimacy,
    )

    try:
        reply = await _call_llm(system_prompt, history)
        reply = _post_process(reply, role)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        reply = "哎，好像有点问题，稍等一下再试试？"

    # 保存 assistant 回复 & 更新状态
    await _session.append_message(user_id, "assistant", reply)
    await _session.bump_intimacy(user_id, emotion.tag)
    await _session.update_state(user_id, emotion_tag=emotion.tag)

    await update.message.reply_text(reply)


# ── 构建 Application ──────────────────────────────────────────────────────────

async def on_startup(app: Application):
    await init_db()
    logger.info("Database initialized.")


def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app
