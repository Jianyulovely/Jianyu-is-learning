from __future__ import annotations

import logging
from dataclasses import dataclass

from config import config
from core.agent.helpers import append_agent_instructions, load_role_for_user
from core.prompt.engine import PromptEngine
from core.memory_manage.memory_model import MemoryQueryContext
from core.memory_manage.memory_service import MemoryService
from core.models import EmotionResult, SystemPromptContext
from core.session.manager import SessionManager
from core.vision.describer import describe_image

logger = logging.getLogger(__name__)


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

    # 图片描述同步生成 (AUDIT B-01)：本轮有图片时，先生成 desc 并写入缓存，再用于 prompt
    if images:
        prompt_image_context = await _describe_and_cache_image(
            session=session, user_id=user_id, image_b64=images[0]
        )
    else:
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


async def _describe_and_cache_image(
    *, session: SessionManager, user_id: int, image_b64: str
) -> str:
    """Synchronous image describe + cache (AUDIT B-01).

    Returns the formatted description text. On failure returns "" so the
    LLM call still proceeds (it gets the raw image, just not the description).
    """
    try:
        desc = await describe_image(image_b64)
    except Exception as exc:
        logger.warning("describe_image failed user_id=%s: %s", user_id, exc)
        return ""
    if not desc:
        return ""
    desc_text = (
        f"场景：{desc.scene}\n"
        f"物体：{', '.join(desc.objects)}\n"
        f"文字：{', '.join(desc.text_ocr)}\n"
        f"用户相关信息：{', '.join(desc.user_relevant_fact)}"
    ).strip()
    try:
        await session.set_last_image_desc(user_id, desc_text)
    except Exception as exc:
        logger.warning("set_last_image_desc failed user_id=%s: %s", user_id, exc)
    return desc_text


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
