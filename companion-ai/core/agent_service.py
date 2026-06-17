from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.models import ChatTurnContext, RequestPayload
from config import config
from core.agent.context import prepare_agent_context, rebuild_system_prompt
from core.agent.helpers import (
    append_assistant_result,
    coerce_user_id,
    first_user_message,
    format_final_reply,
    format_tool_result,
    load_role_for_user,
    normalize_history,
    parse_tool_arguments,
    tool_message,
)
from core.agent.state import AgentTaskState
from core.agent.store import (
    delete_task,
    load_task,
    now_iso,
    save_task,
    task_session_key,
)
from core.emotion.detector import detect as detect_emotion
from core.llm.client import HttpLLMClient, LLMClient, LLMResult
from core.memory_manage.memory_service import MemoryService
from core.messaging.models import InboundMessage, OutboundMessage
from core.prompt.engine import PromptEngine
from core.session.manager import SessionManager
from core.tool.ask_human import AskHuman
from core.tool.tavily_search import TavilySearchTool
from core.tool.terminate import Terminate
from core.tool.tool_collection import ToolCollection

logger = logging.getLogger(__name__)

SPECIAL_ASK_HUMAN = "ask_human"
SPECIAL_TERMINATE = "terminate"


class AgentService:
    def __init__(
        self,
        *,
        session: SessionManager | None = None,
        memory_service: MemoryService | None = None,
        prompt_engine: PromptEngine | None = None,
        llm_client: LLMClient | None = None,
        available_tools: ToolCollection | None = None,
    ) -> None:
        self._session = session or SessionManager()
        self._memory_service = memory_service or MemoryService()
        self._prompt_engine = prompt_engine or PromptEngine()
        self._llm_client = llm_client or HttpLLMClient()
        self._available_tools = available_tools or ToolCollection(
            TavilySearchTool(),
            AskHuman(),
            Terminate(),
        )

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
        user_id = coerce_user_id(msg.sender)
        username = str(msg.metadata.get("username") or "")
        session_key = task_session_key(msg.channel, msg.chat_id)

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

        existing_task = await load_task(session_key)
        if existing_task and existing_task.status == "waiting_human":
            existing_task.messages.append(
                tool_message(
                    tool_call_id=existing_task.pending_tool_call_id or "",
                    name=existing_task.pending_tool_name or SPECIAL_ASK_HUMAN,
                    content=user_message,
                )
            )
            existing_task.status = "running"
            existing_task.pending_tool_call_id = None
            existing_task.pending_tool_name = None
            existing_task.pending_question = None
            existing_task.updated_at = current_time_iso
            await save_task(session_key, existing_task)

            reply = await self._run_agent_loop(
                task=existing_task,
                session_key=session_key,
                user_id=user_id,
                role=load_role_for_user(await self._session.get_user(user_id), username),
                emotion_tag=emotion.tag,
                user_message=user_message,
                prompt_image_context="",
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )
            if existing_task.status != "waiting_human":
                history_user_message = first_user_message(existing_task.messages) or user_message
                await self._after_final_reply(
                    user_id=user_id,
                    user_message=history_user_message,
                    reply=reply,
                    emotion_tag=emotion.tag,
                    prompt_image_context="",
                    current_time_iso=current_time_iso,
                    timezone_name=timezone_name,
                    write_user_history=True,
                )
            return reply

        if existing_task and existing_task.status in {"running", "failed", "done"}:
            await delete_task(session_key)

        prepared = await prepare_agent_context(
            session=self._session,
            memory_service=self._memory_service,
            prompt_engine=self._prompt_engine,
            user_id=user_id,
            username=username,
            user_message=user_message,
            emotion=emotion,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
            images=images,
        )
        role = prepared.role
        role_id = role["role_id"]
        prompt_image_context = prepared.prompt_image_context
        system_prompt = prepared.system_prompt

        history = await self._session.get_history(user_id)
        messages = normalize_history(history)
        messages.append({"role": "user", "content": user_message})

        task = AgentTaskState(
            status="running",
            messages=messages,
            started_at=current_time_iso,
            updated_at=current_time_iso,
        )
        await save_task(session_key, task)

        reply = await self._run_agent_loop(
            task=task,
            session_key=session_key,
            user_id=user_id,
            role=role,
            emotion_tag=emotion.tag,
            user_message=user_message,
            prompt_image_context=prompt_image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
            system_prompt=system_prompt,
            images=images,
        )

        if task.status != "waiting_human":
            await self._after_final_reply(
                user_id=user_id,
                user_message=user_message,
                reply=reply,
                emotion_tag=emotion.tag,
                prompt_image_context=prompt_image_context,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
                write_user_history=True,
            )

        logger.info("[%s] bot (%s): %r", user_id, role_id, reply)
        return reply

    async def _run_agent_loop(
        self,
        *,
        task: AgentTaskState,
        session_key: str,
        user_id: int,
        role: dict[str, Any],
        emotion_tag: str,
        user_message: str,
        prompt_image_context: str,
        current_time_iso: str,
        timezone_name: str,
        system_prompt: str | None = None,
        images: list[str] | None = None,
    ) -> str:
        if system_prompt is None:
            system_prompt = await self._rebuild_system_prompt(
                user_id=user_id,
                username=role.get("username", ""),
                emotion_tag=emotion_tag,
                user_message=user_message,
                prompt_image_context=prompt_image_context,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )

        final_reply = ""
        tools = self._available_tools.to_params()
        images = images or []

        for round_index in range(max(config.MAX_TOOL_ROUNDS, 1)):
            result = await self._llm_client.chat(
                RequestPayload(
                    system_prompt=system_prompt,
                    history_messages=task.messages,
                    images=images if round_index == 0 else [],
                    tools=tools,
                )
            )
            append_assistant_result(task, result)
            task.updated_at = now_iso(timezone_name)
            await save_task(session_key, task)

            if not result.tool_calls:
                final_reply = result.reply
                task.status = "done"
                await delete_task(session_key)
                return format_final_reply(final_reply, role["config"])

            pause_reply = await self._execute_tool_calls(task, session_key, result)
            if pause_reply is not None:
                return pause_reply

        task.messages.append(
            {
                "role": "user",
                "content": (
                    "You have reached the maximum tool rounds. Stop using tools and "
                    "give the best current answer based on the observations so far."
                ),
            }
        )
        task.updated_at = now_iso(timezone_name)
        await save_task(session_key, task)

        try:
            result = await self._llm_client.chat(
                RequestPayload(
                    system_prompt=system_prompt,
                    history_messages=task.messages,
                    tools=[],
                )
            )
            final_reply = result.reply
        except Exception:
            logger.exception("LLM finalization after max tool rounds failed")
            final_reply = "我已经达到本次工具调用上限，暂时只能先停在这里。"

        task.status = "done"
        await delete_task(session_key)
        return format_final_reply(final_reply, role["config"])

    async def _execute_tool_calls(
        self,
        task: AgentTaskState,
        session_key: str,
        result: LLMResult,
    ) -> str | None:
        for tool_call in result.tool_calls:
            call_id = str(tool_call.get("id") or "")
            function = tool_call.get("function") or {}
            name = str(function.get("name") or "")
            arguments = parse_tool_arguments(function.get("arguments"))

            if name == SPECIAL_ASK_HUMAN:
                question = (
                    str(arguments.get("inquire") or arguments.get("question") or "").strip()
                    or result.reply.strip()
                    or "我需要你补充一点信息，才能继续。"
                )
                task.status = "waiting_human"
                task.pending_tool_call_id = call_id
                task.pending_tool_name = name
                task.pending_question = question
                task.updated_at = now_iso(config.USER_TIMEZONE)
                await save_task(session_key, task)
                return question

            tool_result = await self._available_tools.execute(
                name=name,
                tool_input=arguments,
            )
            observation = format_tool_result(tool_result)
            task.messages.append(
                tool_message(tool_call_id=call_id, name=name, content=observation)
            )

            if name == SPECIAL_TERMINATE:
                task.status = "done"
                await delete_task(session_key)
                if result.reply.strip():
                    return format_final_reply(result.reply, {})
                status = str(arguments.get("status") or "").lower()
                if status == "failure":
                    return "任务暂时无法继续，我先停在这里。"
                return "任务已完成。"

            task.updated_at = now_iso(config.USER_TIMEZONE)
            await save_task(session_key, task)

        return None

    async def _rebuild_system_prompt(
        self,
        *,
        user_id: int,
        username: str,
        emotion_tag: str,
        user_message: str,
        prompt_image_context: str,
        current_time_iso: str,
        timezone_name: str,
    ) -> str:
        return await rebuild_system_prompt(
            session=self._session,
            memory_service=self._memory_service,
            prompt_engine=self._prompt_engine,
            user_id=user_id,
            username=username,
            user_message=user_message,
            emotion=detect_emotion(user_message),
            prompt_image_context=prompt_image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )

    async def _after_final_reply(
        self,
        *,
        user_id: int,
        user_message: str,
        reply: str,
        emotion_tag: str,
        prompt_image_context: str,
        current_time_iso: str,
        timezone_name: str,
        write_user_history: bool,
    ) -> None:
        if write_user_history:
            await self._session.append_message(user_id, "user", user_message, emotion_tag)
        await self._session.append_message(user_id, "assistant", reply)
        await self._session.bump_intimacy(user_id, emotion_tag)
        await self._session.update_state(user_id, emotion_tag=emotion_tag)

        chat_turn = ChatTurnContext(
            user_id=user_id,
            user_message=user_message,
            assistant_reply=reply,
            image_context=prompt_image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
        asyncio.create_task(self._memory_service.after_turn(chat_turn))
