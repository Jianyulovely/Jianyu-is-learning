"""
FastAPI LLM 推理服务。
端口 8000，提供 /chat、/health 接口。
"""
import asyncio
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 将 companion-ai 目录加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from llm.model_loader import load_model, get_model


# ── 请求 / 响应模型 ──────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_new_tokens: int = 200
    temperature: float = 0.85
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class ChatResponse(BaseModel):
    reply: str
    usage: dict


# ── App 生命周期 ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(title="Companion AI - LLM Service", lifespan=lifespan)


# ── 推理核心（在线程池中执行，避免阻塞事件循环） ──────────────────────────────

def _inference(req: ChatRequest) -> tuple[str, dict]:
    tokenizer, model = get_model()

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(config.CUDA_DEVICE)
    input_len = inputs.input_ids.shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_new_tokens,
            do_sample=True,
            temperature=req.temperature,
            top_p=req.top_p,
            repetition_penalty=req.repetition_penalty,
            pad_token_id=tokenizer.eos_token_id,
        )

    new_tokens = outputs[0][input_len:]
    reply = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    usage = {
        "input_tokens": int(input_len),
        "output_tokens": int(len(new_tokens)),
    }
    return reply, usage


# ── 路由 ─────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages is empty")
    loop = asyncio.get_event_loop()
    try:
        reply, usage = await loop.run_in_executor(None, _inference, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(reply=reply, usage=usage)


@app.get("/health")
async def health():
    mem_allocated = torch.cuda.memory_allocated() / 1024**3
    mem_reserved = torch.cuda.memory_reserved() / 1024**3
    return {
        "status": "ok",
        "gpu_memory_allocated_gb": round(mem_allocated, 2),
        "gpu_memory_reserved_gb": round(mem_reserved, 2),
    }


# ── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
