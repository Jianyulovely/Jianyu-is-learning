"""
FastAPI LLM 推理服务 - Ollama 封装层
端口 8000，提供 /generate、/health 接口。
"""
import logging
import sys
import os
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


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Companion AI - LLM Service (Ollama)")


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
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(config.OLLAMA_GEN_URL, json=payload)
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


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            resp.raise_for_status()
            return {"status": "ok", "ollama": "connected"}
    except Exception:
        return {"status": "error", "ollama": "disconnected"}


# ── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
