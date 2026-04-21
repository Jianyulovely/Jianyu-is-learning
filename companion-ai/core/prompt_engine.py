"""
Prompt Engine —— 动态组装 System Prompt
结构：基础人设 + 情绪指令 + 记忆摘要（P2 填充）+ few-shot 示例
根据 intimacy_level 注入不同强度的风格描述
"""
import yaml
from pathlib import Path

from core.emotion_detector import EmotionResult

ROLES_DIR = Path(__file__).parent.parent / "roles" / "personas"

# intimacy_level 区间 → 风格补充描述
_INTIMACY_STYLE: list[tuple[int, str]] = [
    (30,  "保持温和知性，偶尔关心，礼貌距离。"),
    (60,  "可以亲昵称呼，主动关心，偶尔撒撒娇。"),
    (80,  "情侣式互动，明显暧昧，甜蜜自然。"),
    (101, "深度情感，亲密依赖感，情感表达更直接。"),
]


# 从人物卡片中加载
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

    def build_system_prompt(
        self,
        role_id: str,
        user_name: str,
        emotion: EmotionResult,
        intimacy_level: int,
        image_context: str = "",
        memory_summary: str = "",
    ) -> str:
        role = self._get_role(role_id)
        parts: list[str] = []

        # 1. 基础人设
        parts.append(role["base_prompt"].strip())

        # 2. 暧昧强度补充
        parts.append(f"当前互动强度指引：{self._intimacy_desc(intimacy_level)}")

        # 3. 情绪指令
        if emotion.tag != "neutral":
            parts.append(
                f"当前{user_name}看起来情绪是【{emotion.tag}】，请注意：{emotion.tone_instruction}"
            )
        else:
            parts.append(emotion.tone_instruction)

        # 4. 当前图片上下文（本条消息携带的图片，静默描述结果）
        if image_context:
            parts.append(f"用户刚发来一张图片，内容是：{image_context}")

        # 5. 长期记忆（P2 注入，P1 阶段留空占位）
        if memory_summary:
            parts.append(f"关于{user_name}你记得：{memory_summary}")

        # 6. few-shot 示例
        few_shot = role.get("few_shot", [])
        if few_shot:
            parts.append("以下是一些对话示例：")
            for ex in few_shot:
                parts.append(f"用户：{ex['user']}")
                parts.append(f"{role['name']}：{ex['assistant']}")

        # 7. 输出格式约束（固定，与角色无关）
        parts.append(
            "【输出格式要求】你的回复将直接显示在 Telegram 消息中。"
            "必须使用简体中文回复，禁止使用繁体中文。"
            "禁止使用 LaTeX 数学公式（$...$、$$...$$、\\frac、\\sum 等）；"
            "用普通文字描述数学内容，例如用'x 的平方'代替'$x^2$'。"
            "禁止使用 Markdown 表格；改用分点列表或分段描述。"
            "可以使用 **加粗** 格式。"
        )

        return "\n".join(parts)
