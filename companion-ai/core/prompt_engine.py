from pathlib import Path

import yaml

from core.models import SystemPromptContext


ROLES_DIR = Path(__file__).parent.parent / "roles" / "personas"

_INTIMACY_STYLE: list[tuple[int, str]] = [
    (30, "当前关系偏陌生，回复要自然、礼貌，不要过度亲密。"),
    (60, "当前关系在逐渐熟悉，可以更温和、更有陪伴感，但仍然要克制。"),
    (80, "当前关系比较熟悉，可以更贴心一些，适度表达关心和理解。"),
    (101, "当前关系已经较亲近，可以自然表达在意和陪伴感，但不要失控或越界。"),
]


def _load_role(role_id: str) -> dict:
    path = ROLES_DIR / f"{role_id}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class PromptEngine:
    def __init__(self):
        self._cache: dict[str, dict] = {}

    def _get_role(self, role_id: str) -> dict:
        if role_id not in self._cache:
            self._cache[role_id] = _load_role(role_id)
        return self._cache[role_id]

    def _intimacy_desc(self, level: int) -> str:
        for threshold, desc in _INTIMACY_STYLE:
            if level < threshold:
                return desc
        return _INTIMACY_STYLE[-1][1]

    def build_system_prompt(self, context: SystemPromptContext) -> str:
        
        role_id = context.role_id
        user_name = context.user_name
        emotion = context.emotion
        intimacy_level = context.intimacy_level
        current_time_iso = context.current_time_iso
        timezone_name = context.timezone_name
        image_context = context.image_context
        memory_summary = context.memory_summary
        
        role = self._get_role(role_id)
        parts: list[str] = []

        base_prompt = str(role.get("base_prompt", "")).strip()
        if base_prompt:
            parts.append(base_prompt)

        parts.append(self._intimacy_desc(intimacy_level))

        if context.emotion.tag != "neutral":
            parts.append(
                f"{user_name} 当前情绪倾向是 {emotion.tag}。回复时请注意：{emotion.tone_instruction}"
            )
        elif emotion.tone_instruction:
            parts.append(str(emotion.tone_instruction))

        if current_time_iso:
            if timezone_name:
                parts.append(
                    f"当前时间是 {current_time_iso}，时区是 {timezone_name}。请正确理解今天、明天、下周等相对时间。"
                )
            else:
                parts.append(
                    f"当前时间是 {current_time_iso}。请正确理解今天、明天、下周等相对时间。"
                )

        if image_context:
            parts.append(f"用户最近发送过一张图片，内容描述是：{image_context}")

        if memory_summary:
            parts.append(f"关于 {user_name}，你记得这些长期信息：\n{memory_summary}")

        # 先不要few_shot，感觉作用不大还占token...
        """
        few_shot = role.get("few_shot", []) or []
        if few_shot:
            parts.append("下面是角色语气示例，请参考语气，不要机械复读：")
            role_name = str(role.get("name", role_id))
            for ex in few_shot:
                user_example = str(ex.get("user", "")).strip()
                assistant_example = str(ex.get("assistant", "")).strip()
                if user_example:
                    parts.append(f"用户：{user_example}")
                if assistant_example:
                    parts.append(f"{role_name}：{assistant_example}")
        """

        parts.append(
            "请保持自然、连贯、口语化的中文表达。"
            "适合 Telegram 聊天场景。"
            "不要输出系统设定说明。"
            "如果包含公式，使用标准 LaTeX 形式。"
            "可以使用 Markdown 加粗重点，但不要滥用。"
        )

        return "\n".join(part for part in parts if part)
