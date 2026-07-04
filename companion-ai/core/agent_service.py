"""AgentService: thin Flow router + Telegram glue.

Layering (since P3):
    InboundMessage → AgentService.handle()
                       ├─ prepare context (session/role/emotion/prompt/history)
                       ├─ load existing AgentTaskState (if any)
                       ├─ delegate to PlanningFlow.execute(context)
                       │     ├─ chat-mode task → ChatFlow (waiting_human resume etc.)
                       │     ├─ planning-mode task → step routing
                       │     └─ fresh task → decide chat vs plan
                       ├─ optionally write to session.history
                       └─ wrap reply into OutboundMessage

Approval semantics (``_is_approval_reply``) live here because they're the
business policy that PlanningFlow / ChatFlow inject — not part of the
agent loop primitives.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.models import ChatTurnContext
from config import config
from core.agent.context import prepare_agent_context
from core.agent.helpers import (
    coerce_user_id,
    normalize_history,
)
from core.agent.state import AgentTaskState
from core.agent.store import (
    delete_task,
    load_task,
    task_session_key,
)
from core.emotion.detector import detect as detect_emotion
from core.flow.planning import AgentBuilder, PlanningFlow as TurnFlow
from core.llm.client import HttpLLMClient, LLMClient
from core.memory_manage.memory_service import MemoryService
from core.messaging.models import InboundMessage, OutboundMessage
from core.prompt.engine import PromptEngine
from core.session.manager import SessionManager
from core.tool.ask_human import AskHuman
from core.tool.computer import ComputerShellTool
from core.tool.file_editor import StrReplaceEditor
from core.tool.planning import PlanningTool
from core.tool.tavily_search import TavilySearchTool
from core.tool.terminate import Terminate
from core.tool.tool_collection import ToolCollection

logger = logging.getLogger(__name__)

# 同意词整词匹配集合。先扫否定词避免 "不可以" 误判为同意 (AUDIT P-01)。
APPROVAL_WORDS_CN = {
    "可以", "嗯", "嗯呢", "好", "好的", "同意", "确认", "允许", "批准",
    "行", "没问题",
}
APPROVAL_WORDS_EN = {"yes", "y", "ok", "okay", "sure", "confirm", "approve"}
REJECT_WORDS_CN = {
    "不", "不要", "不可以", "不行", "不好", "不同意", "不允许", "不能",
    "拒绝", "取消", "停", "停止", "算了", "别",
}
REJECT_WORDS_EN = {"no", "nope", "cancel", "stop", "abort", "never", "deny", "reject"}

# 审批回复通常极短，超过此长度即视为聊天/陈述，不再判同意 (AUDIT P-01 edge case)
_APPROVAL_MAX_LEN = 20


class AgentService:
    """Orchestrates one inbound message into a reply via Flow layer."""

    def __init__(
        self,
        *,
        session: SessionManager | None = None,
        memory_service: MemoryService | None = None,
        prompt_engine: PromptEngine | None = None,
        llm_client: LLMClient | None = None,
        available_tools: ToolCollection | None = None,
        plan_agents: dict[str, AgentBuilder] | None = None,
    ) -> None:
        self._session = session or SessionManager()
        self._memory_service = memory_service or MemoryService()
        self._prompt_engine = prompt_engine or PromptEngine()
        self._llm_client = llm_client or HttpLLMClient()
        self._available_tools = available_tools or ToolCollection(
            PlanningTool(stage="execute"),
            StrReplaceEditor(),
            TavilySearchTool(),
            ComputerShellTool(),
            AskHuman(),
            Terminate(),
        )
        self._flow = TurnFlow(
            llm=self._llm_client,
            available_tools=self._available_tools,
            is_approval_reply=self._is_approval_reply,
            agents=plan_agents,
        )

    # ---- public API ------------------------------------------------------

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

    # ---- core ------------------------------------------------------------

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
            user_id, msg.channel, msg.chat_id, user_message, emotion.tag,
        )

        existing_task = await self._load_and_cleanup_task(session_key)

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

        history = await self._session.get_history(user_id)
        history_messages = normalize_history(history)

        context = {
            "session_key": session_key,
            "user_id": user_id,
            "user_message": user_message,
            "role": prepared.role,
            "emotion_tag": emotion.tag,
            "prompt_image_context": prepared.prompt_image_context,
            "current_time_iso": current_time_iso,
            "timezone_name": timezone_name,
            "system_prompt": prepared.system_prompt,
            "images": images,
            "task": existing_task,
            "history_messages": history_messages,
        }

        outcome = await self._flow.execute(context=context)
        reply = outcome.reply

        if outcome.write_history:
            history_user = outcome.history_user_message or user_message
            await self._after_final_reply(
                user_id=user_id,
                user_message=history_user,
                reply=reply,
                emotion_tag=emotion.tag,
                prompt_image_context=prepared.prompt_image_context,
                current_time_iso=current_time_iso,
                timezone_name=timezone_name,
            )

        logger.info("[%s] bot (%s): %r", user_id, prepared.role["role_id"], reply)
        return reply

    # ---- helpers ---------------------------------------------------------

    async def _load_and_cleanup_task(self, session_key: str) -> AgentTaskState | None:
        """Load persisted task; drop terminal states.

        Running tasks survive (a previous turn may have crashed mid-loop —
        ``BaseAgent.state_context`` will flip to ``failed`` next time and trip
        this cleanup).
        """
        task = await load_task(session_key)
        if task and task.status in {"done", "failed"}:
            await delete_task(session_key)
            return None
        return task

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
    ) -> None:
        await self._session.append_message(user_id, "user", user_message, emotion_tag)
        await self._session.append_message(user_id, "assistant", reply)
        await self._session.bump_intimacy(user_id, emotion_tag)
        await self._session.update_state(user_id, emotion_tag=emotion_tag)

        # Memory extraction currently disabled — see core/memory_manage.
        _ = ChatTurnContext(
            user_id=user_id,
            user_message=user_message,
            assistant_reply=reply,
            image_context=prompt_image_context,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )

    # ---- approval policy (used by Flow layer) ----------------------------

    def _is_approval_reply(self, text: str) -> bool:
        """
        判断用户的回复是否为"批准/确认"指令
        """
        raw = text.strip()
        if not raw:
            return False
        if len(raw) >= _APPROVAL_MAX_LEN:
            return False
        lowered = raw.lower()
        if self._contains_chinese_word(raw, REJECT_WORDS_CN):
            return False
        if self._contains_english_word(lowered, REJECT_WORDS_EN):
            return False
        if self._contains_chinese_word(raw, APPROVAL_WORDS_CN):
            return True
        if self._contains_english_word(lowered, APPROVAL_WORDS_EN):
            return True
        return False

    @staticmethod
    def _contains_chinese_word(text: str, words: set[str]) -> bool:
        return any(word in text for word in words)

    @staticmethod
    def _contains_english_word(text_lower: str, words: set[str]) -> bool:
        tokens = set(re.findall(r"[a-z]+", text_lower))
        return bool(tokens & words)
