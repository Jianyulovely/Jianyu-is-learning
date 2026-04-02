# main.py
import os
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx, json
import uvicorn

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

API_TOKEN = (os.getenv("LLM_API_TOKEN") or "").strip()

app = FastAPI()
OLLAMA_GEN_URL = (os.getenv("OLLAMA_GEN_URL") or "").strip()
OLLAMA_CHAT_URL = (os.getenv("OLLAMA_CHAT_URL") or "").strip()
MODEL = (os.getenv("OLLAMA_MODEL") or "").strip()

class ChatRequest(BaseModel):
    messages: list[dict]
    stream: bool = True

class GenerateRequest(BaseModel):
    content: str
    stream: bool = False

async def verify_token(authorization: str = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=401)

@app.post("/chat", dependencies=[Depends(verify_token)])
async def chat(req: ChatRequest):
    payload = {
        "model": MODEL,
        "messages": req.messages,
        "stream": req.stream,
    }

    # 针对流式输出
    if req.stream:
        async def generate():
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", OLLAMA_CHAT_URL, json=payload) as r:
                    async for line in r.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if content := data.get("message", {}).get("content"):
                                yield content
        return StreamingResponse(generate(), media_type="text/plain")
    
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(OLLAMA_CHAT_URL, json=payload)
        return r.json()


@app.post("/generate", dependencies=[Depends(verify_token)])
async def generate(req: GenerateRequest):
    payload = {
        "model": MODEL,
        "prompt": req.content,
        "stream": req.stream,
    }

    # 针对流式输出
    if req.stream:
        async def stream_generate():
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", OLLAMA_GEN_URL, json=payload) as r:
                    async for line in r.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if content := data.get("response"):
                                yield content
                            if data.get("done"):
                                break
        return StreamingResponse(stream_generate(), media_type="text/plain")
    
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(OLLAMA_GEN_URL, json=payload)
        return r.json()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=1212, workers=1)  # 在指定端口和主机上启动应用