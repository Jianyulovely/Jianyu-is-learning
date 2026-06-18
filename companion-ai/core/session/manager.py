from __future__ import annotations

from typing import Optional

from core.session.cleanup import (
    clear_history as clear_history_data,
    reset_all as reset_all_data,
)
from core.session.history import (
    append_message as append_history_message,
    get_history as get_history_messages,
)
from core.session.image import (
    get_last_image_desc as get_cached_image_desc,
    save_image_memory as persist_image_memory,
    set_last_image_desc as cache_image_desc,
)
from core.session.state import (
    bump_intimacy as update_intimacy,
    get_intimacy as get_user_intimacy,
    get_state as get_session_state,
    update_state as set_session_state,
)
from core.session.user import (
    ensure_user as ensure_session_user,
    get_user as get_session_user,
    set_nickname as update_user_nickname,
    set_role as update_user_role,
)


class SessionManager:
    async def get_history(self, user_id: int) -> list[dict]:
        return await get_history_messages(user_id)

    async def append_message(
        self,
        user_id: int,
        role: str,
        content: str,
        emotion_tag: str = "neutral",
    ):
        _ = emotion_tag
        await append_history_message(user_id, role, content)

    async def get_state(self, user_id: int) -> dict:
        return await get_session_state(user_id)

    async def update_state(self, user_id: int, **kwargs):
        await set_session_state(user_id, **kwargs)

    async def get_intimacy(self, user_id: int) -> int:
        return await get_user_intimacy(user_id)

    async def bump_intimacy(self, user_id: int, emotion_tag: str):
        await update_intimacy(user_id, emotion_tag)

    async def ensure_user(self, user_id: int, username: str = "", role_id: str = "Alex"):
        await ensure_session_user(user_id, username, role_id)

    async def get_user(self, user_id: int) -> Optional[dict]:
        return await get_session_user(user_id)

    async def set_role(self, user_id: int, role_id: str):
        await update_user_role(user_id, role_id)

    async def clear_history(self, user_id: int):
        """Clear conversation history only — intimacy is preserved (AUDIT B-04)."""
        await clear_history_data(user_id)

    async def reset_all(self, user_id: int):
        """Hard reset including intimacy and state. Use sparingly."""
        await reset_all_data(user_id)

    async def get_last_image_desc(self, user_id: int) -> str:
        return await get_cached_image_desc(user_id)

    async def set_last_image_desc(self, user_id: int, desc: str):
        await cache_image_desc(user_id, desc)

    async def save_image_memory(self, user_id: int, desc: str):
        await persist_image_memory(user_id, desc)

    async def set_nickname(self, user_id: int, nickname: str):
        await update_user_nickname(user_id, nickname)
