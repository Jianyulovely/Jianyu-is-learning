"""
Telegram Bot Handler —— P0 MVP
职责：接收消息 → 维护内存会话 → 调用 LLM API → 回复用户
"""
import logging
from pathlib import Path

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

logger = logging.getLogger(__name__)

# ── 角色配置加载 ──────────────────────────────────────────────────────────────

def _load_role(role_name: str) -> dict:
    path = config.ROLES_DIR / f"{role_name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


ROLE = _load_role(config.DEFAULT_ROLE)


def _build_system_prompt() -> str:
    """P0：固定 system prompt = 基础人设 + few-shot"""
    lines = [ROLE["base_prompt"].strip(), ""]
    lines.append("以下是一些对话示例：")
    for ex in ROLE.get("few_shot", []):
        lines.append(f"用户：{ex['user']}")
        lines.append(f"{ROLE['name']}：{ex['assistant']}")
    return "\n".join(lines)


SYSTEM_PROMPT = _build_system_prompt()

# ── 内存会话（P0 简化版，key = user_id） ──────────────────────────────────────
# 每个用户保存最近 MAX_HISTORY_TURNS * 2 条消息（user + assistant 各算1条）
_sessions: dict[int, list[dict]] = {}


def _get_history(user_id: int) -> list[dict]:
    return _sessions.setdefault(user_id, [])


def _append_history(user_id: int, role: str, content: str):
    history = _get_history(user_id)
    history.append({"role": role, "content": content})
    max_msgs = config.MAX_HISTORY_TURNS * 2
    if len(history) > max_msgs:
        _sessions[user_id] = history[-max_msgs:]


# ── LLM API 调用 ──────────────────────────────────────────────────────────────

async def _call_llm(user_id: int, user_text: str) -> str:

    _append_history(user_id, "user", user_text)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _get_history(user_id)

    payload = {
        "messages": messages,
        "max_new_tokens": 200,
        "temperature": 0.85,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    }

    async with httpx.AsyncClient(
            timeout=120.0,
            transport=httpx.AsyncHTTPTransport(retries=1)
        ) as client:
        resp = await client.post(
                    f"{config.LLM_API_URL}/chat", 
                    json=payload, 
                    headers={"Connection": "close"}   # 👉 禁用连接复用（关键）
                )
        resp.raise_for_status()
        data = resp.json()

    reply: str = data["reply"]

    # Post-process: 过滤禁用短语，必要时截断
    for phrase in ROLE.get("forbidden_phrases", []):
        if phrase in reply:
            logger.warning("Forbidden phrase detected, returning fallback.")
            reply = "嗯……有点走神了，你刚才说什么来着？"
            break

    _append_history(user_id, "assistant", reply)
    return reply


# ── 指令处理 ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "你"
    await update.message.reply_text(
        f"嗨，{name}～我是惠惠。有什么想聊的嘛，直接说就好。"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _sessions.pop(user_id, None)
    await update.message.reply_text("好，我们重新开始聊吧～")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/start  —  开始对话\n"
        "/reset  —  清除当前会话记录\n"
        "/help   —  查看指令列表"
    )
    await update.message.reply_text(text)


# ── 普通消息处理 ──────────────────────────────────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

    # 发送"正在输入"状态
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        reply = await _call_llm(user_id, text)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        reply = "哎，好像有点问题，稍等一下再试试？"

    await update.message.reply_text(reply)


# ── 构建 Application ──────────────────────────────────────────────────────────

def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app
