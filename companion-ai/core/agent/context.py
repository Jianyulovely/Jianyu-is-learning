from __future__ import annotations

from dataclasses import dataclass

from config import config
from core.agent.helpers import append_agent_instructions, load_role_for_user
from core.prompt.engine import PromptEngine
from core.memory_manage.memory_model import MemoryQueryContext
from core.memory_manage.memory_service import MemoryService
from core.models import EmotionResult, SystemPromptContext
from core.session.manager import SessionManager


@dataclass
class PreparedAgentContext:
    role: dict
    prompt_image_context: str
    system_prompt: str


async def prepare_agent_context(
    *,
    session: SessionManager,
    memory_service: MemoryService,
    prompt_engine: PromptEngine,
    user_id: int,
    username: str,
    user_message: str,
    emotion: EmotionResult,
    current_time_iso: str,
    timezone_name: str,
    images: list[str] | None = None,
) -> PreparedAgentContext:
    db_user = await session.get_user(user_id)
    role = load_role_for_user(db_user, username)
    intimacy = await session.get_intimacy(user_id)

    prompt_image_context = ""
    if not images:
        prompt_image_context = await session.get_last_image_desc(user_id)

    memory_summary = await memory_service.build_memory_summary(
        MemoryQueryContext(
            user_id=user_id,
            query=user_message,
            current_time_iso=current_time_iso,
            timezone_name=timezone_name,
        )
    )

    prompt_context = SystemPromptContext(
        role_id=role["role_id"],
        user_name=role["user_name"],
        emotion=emotion,
        intimacy_level=intimacy,
        image_context=prompt_image_context,
        memory_summary=memory_summary,
        current_time_iso=current_time_iso,
        timezone_name=timezone_name,
    )
    system_prompt = append_agent_instructions(
        prompt_engine.build_system_prompt(prompt_context)
    )

    return PreparedAgentContext(
        role=role,
        prompt_image_context=prompt_image_context,
        system_prompt=system_prompt,
    )


async def rebuild_system_prompt(
    *,
    session: SessionManager,
    memory_service: MemoryService,
    prompt_engine: PromptEngine,
    user_id: int,
    username: str,
    user_message: str,
    emotion: EmotionResult,
    prompt_image_context: str,
    current_time_iso: str,
    timezone_name: str,
) -> str:
    db_user = await session.get_user(user_id)
    role_id = (db_user or {}).get("role_id", config.DEFAULT_ROLE)
    user_name = (db_user or {}).get("nickname") or username or "用户"
    intimacy = await session.get_intimacy(user_id)
    memory_summary = await memory_service.build_memory_summary(
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
    return append_agent_instructions(prompt_engine.build_system_prompt(prompt_context))
