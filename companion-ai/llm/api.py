"""
FastAPI LLM 推理服务
端口 8000，提供 /generate（图片描述）、/chat（多轮对话）、/health 接口。
/chat 通过 OpenAI 兼容接口调用，支持本地 Ollama 和外部 API（DeepSeek、OpenAI 等）。
/generate 仍使用 Ollama 原生接口（依赖 context token 的图片描述后台任务）。
"""
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
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


_llm_client: AsyncOpenAI | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _llm_client
    _llm_client = AsyncOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        timeout=120.0,
    )
    yield
    await http_client.aclose()
    await _llm_client.close()


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

    logger.info(f"→ chat messages: {len(req.messages)} 条, model: {config.LLM_MODEL}")
    logger.info(f"→ system_prompt:\n{req.system_prompt}")

    messages = [{"role": "system", "content": req.system_prompt}]
    for i, m in enumerate(req.messages):
        is_last_user = (i == len(req.messages) - 1 and m.role == "user")
        # 用户本次消息同时有图片和文字
        if req.images and is_last_user:
            # OpenAI vision 格式，Ollama /v1 同样支持
            messages.append({
                "role": m.role,  
                "content": [
                    {"type": "text", "text": m.content},
                    *[{"type": "image_url",
                       "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                      for img in req.images],
                ],
            })
        else:
            msg: dict = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            messages.append(msg)

    try:
        kwargs: dict = dict(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=req.temperature,
            top_p=req.top_p,
        )
        if req.tools:
            kwargs["tools"] = req.tools

        resp = await _llm_client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        reply = choice.message.content or ""
        tool_calls = []
        if choice.message.tool_calls:
            tool_calls = [
                {"id": tc.id,
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in choice.message.tool_calls
            ]
        logger.info(f"← reply: {reply!r}  tool_calls: {len(tool_calls)}")

        return ChatResponse(
            reply=reply,
            tool_calls=tool_calls,
            usage={"total_tokens": resp.usage.total_tokens if resp.usage else 0},
        )
    except Exception as e:
        logger.exception("Chat request failed")
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
