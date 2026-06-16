from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

from bot.models import ChatTurnContext, RequestPayload
from config import config
from core.emotion_detector import detect as detect_emotion
from core.formatter import format_reply
from core.llm_client import HttpLLMClient, LLMClient
from core.memory_manage.memory_service import MemoryQueryContext, MemoryService
from core.messages import InboundMessage, OutboundMessage
from core.models import SystemPromptContext
from core.prompt_engine import PromptEngine
from core.session_manager import SessionManager
from core.tools import execute_tool, select_tools

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        *,
        session: SessionManager | None = None,
        memory_service: MemoryService | None = None,
        prompt_engine: PromptEngine | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._session = session or SessionManager()
        self._memory_service = memory_service or MemoryService()
        self._prompt_engine = prompt_engine or PromptEngine()
        self._llm_client = llm_client or HttpLLMClient()

    async def handle(self, msg: InboundMessage) -> OutboundMessage:
        try:
            reply = await self._handle_message(msg)
        except Exception:
            logger.exception(
                "Agent turn failed channel=%s chat_id=%s sender=%s",
                msg.channel,
                msg.chat_id,
                msg.sender,
            )
            reply = "我这边刚才有点卡住了，你可以再发一次，我继续接。"
        return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=reply)

    async def _handle_message(self, msg: InboundMessage) -> str:
        user_message = msg.content.strip()
        images = list(msg.media or [])
        user_id = _coerce_user_id(msg.sender)
        username = str(msg.metadata.get("username") or "")

        timezone_name = config.USER_TIMEZONE
        current_time_iso = datetime.now(ZoneInfo(timezone_name)).isoformat()

        await self._session.ensure_user(user_id, username)

        emotion = detect_emotion(user_message)
        logger.info(
            "[%s] user channel=%s chat_id=%s content=%r emotion=%s",
            user_id,
            msg.channel,
            msg.chat_id,
            user_message,
            emotion.tag,
        )

        intimacy = await self._session.get_intimacy(user_id)
        db_user = await self._session.get_user(user_id)
        user_name = (db_user or {}).get("nickname") or username or "用户"
        role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
        role = _load_role(role_id)

        await self._session.append_message(user_id, "user", user_message, emotion.tag)

        prompt_image_context = ""
        if not images:
            prompt_image_context = await self._session.get_last_image_desc(user_id)

        memory_summary = await self._memory_service.build_memory_summary(
            MemoryQueryContext(
                user_id=user_id,
                query=user_message,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )
        )

        prompt_context = SystemPromptContext(
            role_id=role_id,
            user_name=user_name,
            emotion=emotion,
            intimacy_level=intimacy,
            image_context=prompt_image_context,
            memory_summary=memory_summary,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
        system_prompt = self._prompt_engine.build_system_prompt(prompt_context)

        tools_schemas, history = await asyncio.gather(
            select_tools(user_message),
            self._session.get_history(user_id),
        )
        tool_context = await _execute_selected_tools(tools_schemas, user_message)

        reply = await self._llm_client.chat(
            RequestPayload(
                system_prompt=system_prompt,
                history_messages=history,
                images=images,
                tool_context=tool_context,
            )
        )
        reply = _post_process(reply, role)
        reply = format_reply(reply)

        if not reply.strip():
            logger.warning("[%s] empty reply from LLM, raw: %r", user_id, reply)
            reply = "我刚才没组织好这句话，你再说一句，我接着陪你聊。"

        logger.info("[%s] bot (%s): %r", user_id, role_id, reply)

        await self._session.append_message(user_id, "assistant", reply)
        await self._session.bump_intimacy(user_id, emotion.tag)
        await self._session.update_state(user_id, emotion_tag=emotion.tag)

        chat_turn = ChatTurnContext(
            user_id=user_id,
            user_message=user_message,
            assistant_reply=reply,
            image_context=prompt_image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
        asyncio.create_task(self._memory_service.after_turn(chat_turn))

        return reply


async def _execute_selected_tools(tools: list[dict], user_message: str) -> str:
    if not tools:
        return ""

    results = await asyncio.gather(
        *[
            execute_tool(tool["function"]["name"], {"query": user_message})
            for tool in tools
        ],
        return_exceptions=True,
    )
    parts: list[str] = []
    for tool, result in zip(tools, results):
        name = tool["function"]["name"]
        result_text = str(result or "")
        preview = result_text[:200]
        logger.info("[tool_exec] %s result preview: %r", name, preview)
        parts.append(f"[{name}]\n{result_text}")
    context = "\n\n".join(parts)
    logger.info("[tool_context] total_len=%s", len(context))
    return context


def _post_process(reply: str, role: dict) -> str:
    for phrase in role.get("forbidden_phrases", []):
        if phrase and phrase in reply:
            logger.warning("Forbidden phrase detected, using fallback.")
            return "我换一种更自然的说法继续和你聊。"
    return reply


def _load_role(role_id: str) -> dict:
    path = config.ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _coerce_user_id(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return abs(hash(str(value))) % (2**31)
