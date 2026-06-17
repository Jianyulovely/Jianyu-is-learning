from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from bot.models import RequestPayload
from config import config
from core.net.http import safe_post

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    reply: str
    tool_calls: list[dict]
    usage: dict


class LLMClient(Protocol):
    async def chat(self, payload: RequestPayload) -> LLMResult:
        ...


class HttpLLMClient:
    async def chat(self, payload: RequestPayload) -> LLMResult:
        system_prompt = payload.system_prompt
        effective_messages = list(payload.history_messages)

        if payload.tool_context:
            system_prompt = (
                system_prompt
                + "\n\n以下是工具返回的外部信息。仅在相关时引用，不要生硬照搬，也不要编造成你亲自经历过。"
            )
            if effective_messages and effective_messages[-1]["role"] == "user":
                last = effective_messages[-1]
                effective_messages[-1] = {
                    **last,
                    "content": f"[工具上下文]\n{payload.tool_context}\n\n---\n{last['content']}",
                }
            else:
                effective_messages.append(
                    {"role": "user", "content": f"[工具上下文]\n{payload.tool_context}"}
                )

        request_body = {
            "system_prompt": system_prompt,
            "messages": effective_messages,
            "images": payload.images,
            "tools": payload.tools,
            "response_format": payload.response_format,
            "temperature": payload.temperature,
            "top_p": payload.top_p,
        }
        resp = await safe_post(f"{config.LLM_API_URL}/chat", json=request_body)
        if resp.status_code >= 400:
            logger.error("LLM /chat failed: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
        data = resp.json()
        return LLMResult(
            reply=data.get("reply", ""),
            tool_calls=data.get("tool_calls", []) or [],
            usage=data.get("usage", {}) or {},
        )
