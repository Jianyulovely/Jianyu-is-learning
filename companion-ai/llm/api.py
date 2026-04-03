"""
FastAPI LLM 推理服务 - Ollama 封装层
端口 8000，提供 /generate、/health 接口。
"""
import sys
import os
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 将 companion-ai 目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


# ── 请求 / 响应模型 ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200
    temperature: float = 0.85
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class GenerateResponse(BaseModel):
    reply: str
    usage: dict


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Companion AI - LLM Service (Ollama)")


# ── 路由 ─────────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt is empty")

    # 构建 Ollama 请求
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": req.prompt,
        "stream": False,
        "options": {
            "num_predict": req.max_new_tokens,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "repeat_penalty": req.repetition_penalty,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(config.OLLAMA_GEN_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return GenerateResponse(
                reply=data.get("response", ""),
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
