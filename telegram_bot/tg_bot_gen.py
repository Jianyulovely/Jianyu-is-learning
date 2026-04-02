import os
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 尝试从 .env 加载（可选）
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# ===== 配置区 =====
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
API_TOKEN = (os.getenv("LLM_API_TOKEN") or "").strip()
LLM_URL = (os.getenv("LLM_URL") or "").strip()
# ==================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 使用ollama/generate 功能，输入输出可以参考官方api
async def ask_llm(prompt: str) -> str:
    try:
        logging.info(f"LLM_URL: {LLM_URL}")
        logging.info(f"API_TOKEN 长度: {len(API_TOKEN)}")
        logging.info(f"正在请求 LLM，prompt: {prompt}")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{LLM_URL}/generate",
                json={
                    "content": prompt,
                    "stream": False
                },
                headers={"Authorization": f"Bearer {API_TOKEN}"} 
            )
            logging.info(f"状态码: {response.status_code}")
            logging.info(f"返回内容: {response.text}")  # ← 关键，看原始返回
            response.raise_for_status()
            # FastAPI 非流式时直接返回 Ollama 的响应
            data = response.json()
            return data["response"]
    except Exception as e:
        logging.error(f"调用 LLM 失败: {type(e).__name__}: {e}")
        return "⚠️ LLM 服务暂时无法访问，请稍后再试。"


async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("用法：/ask 你想问的问题")
        return
    thinking_msg = await update.message.reply_text("🤔 思考中...")
    reply = await ask_llm(prompt)
    await thinking_msg.edit_text(reply)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 你好！我是 LLM Bot。\n\n使用方式：\n/ask 你想问的问题"
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "未找到 TELEGRAM_BOT_TOKEN。请在项目根目录创建 .env 并设置：\n"
            "TELEGRAM_BOT_TOKEN=xxxx:yyyy （或设置环境变量 BOT_TOKEN/TELEGRAM_BOT_TOKEN）"
        )
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("ask", ask_handler))
    print("Bot 启动成功，开始监听消息...")
    app.run_polling()


if __name__ == "__main__":
    main()