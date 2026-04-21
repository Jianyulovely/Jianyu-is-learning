"""
FastAPI LLM 推理服务 - Ollama 封装层
端口 8000，提供 /generate（图片描述）、/chat（多轮对话）、/health 接口。
"""
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 将 companion-ai 目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
import core.http_client as http_client
from core.http_client import safe_post, safe_get


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await http_client.aclose()


# ── 请求 / 响应模型 ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    system_prompt: str
    user_message: str
    images: list[str] = []       # base64 编码图片列表，无图传 []
    context: list[int] = []      # Ollama 多轮上下文 token，首轮传 []
    max_new_tokens: int = 200
    temperature: float = 0.85
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class GenerateResponse(BaseModel):
    reply: str
    context: list[int]           # 透传给调用方，存入 Redis 供下轮使用
    usage: dict


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[dict] = []


class ChatRequest(BaseModel):
    system_prompt: str
    messages: list[ChatMessage]
    images: list[str] = []
    tools: list[dict] = []
    temperature: float = 0.85
    top_p: float = 0.9


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []
    usage: dict


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Companion AI - LLM Service (Ollama)", lifespan=lifespan)


# ── 路由 ─────────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if not req.user_message:
        raise HTTPException(status_code=400, detail="user_message is empty")

    logger.info(f"→ user_message: {req.user_message!r}")
    logger.info(f"→ images: {len(req.images)} 张, context tokens: {len(req.context)}")
    logger.info(f"→ system_prompt:\n{req.system_prompt}")

    payload = {
        "model": config.OLLAMA_MODEL,
        "system": req.system_prompt,
        "prompt": req.user_message,
        "stream": False,
        "options": {
            # 注意：num_predict 不能与其他同时存在
            # "num_predict": req.max_new_tokens,
            "temperature": req.temperature,
            "top_p": req.top_p,
        },
    }
    if req.images:
        payload["images"] = req.images
    if req.context:
        payload["context"] = req.context

    try:
        resp = await safe_post(config.OLLAMA_GEN_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("response", "")
        logger.info(f"← reply: {reply!r}")
        logger.info(f"← context tokens: {len(data.get('context', []))}")

        return GenerateResponse(
            reply=reply,
            context=data.get("context", []),
            usage={"input_tokens": 0, "output_tokens": 0}
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Ollama request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages is empty")

    logger.info(f"→ chat messages: {len(req.messages)} 条")
    logger.info(f"→ system_prompt:\n{req.system_prompt}")

    ollama_messages = [{"role": "system", "content": req.system_prompt}]
    for i, m in enumerate(req.messages):
        msg = {"role": m.role, "content": m.content}
        if m.tool_calls:
            msg["tool_calls"] = m.tool_calls
        if req.images and i == len(req.messages) - 1 and m.role == "user":
            msg["images"] = req.images
        ollama_messages.append(msg)

    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "temperature": req.temperature,
            "top_p": req.top_p,
        },
    }
    if req.tools:
        payload["tools"] = req.tools

    try:
        resp = await safe_post(config.OLLAMA_CHAT_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("message", {})
        reply = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])
        logger.info(f"← reply: {reply!r}  tool_calls: {len(tool_calls)}")

        return ChatResponse(
            reply=reply,
            tool_calls=tool_calls,
            usage={"input_tokens": 0, "output_tokens": 0},
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Ollama request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    try:
        resp = await safe_get("http://localhost:11434/api/tags", timeout=5.0)
        resp.raise_for_status()
        return {"status": "ok", "ollama": "connected"}
    except Exception:
        return {"status": "error", "ollama": "disconnected"}


# ── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
