"""
Emotion Detector —— 基于关键词匹配的情绪识别
返回情绪标签和对应的语气调整指令
"""
from dataclasses import dataclass

_RULES: list[tuple[str, list[str]]] = [
    ("happy",    ["哈哈", "开心", "太棒", "耶", "好棒", "高兴", "嘿嘿", "哈哈哈", "棒棒", "开森", "爽"]),
    ("sad",      ["难过", "不开心", "好累", "哭", "伤心", "委屈", "郁闷", "心情差", "想哭", "难受"]),
    ("stressed", ["烦死了", "压力", "好烦", "崩了", "焦虑", "烦躁", "头疼", "好累了", "撑不住", "好难"]),
    ("romantic", ["喜欢你", "想你", "好想", "亲", "爱你", "想见你", "想抱", "心动", "暗恋"]),
]

_TONE_MAP: dict[str, str] = {
    "happy":    "用户心情不错，保持活泼，同频共振，可以稍微俏皮一点。",
    "sad":      "用户情绪低落，温柔安慰，放慢节奏，多倾听少建议。",
    "stressed": "用户压力较大，先共情再疏导，语气轻柔，不要急着给解决方案。",
    "romantic": "用户流露出情感信号，可以适度升温回应，甜蜜但不过分直白。",
    "neutral":  "保持角色基础风格即可。",
}


@dataclass
class EmotionResult:
    tag: str
    tone_instruction: str


def detect(text: str) -> EmotionResult:
    for tag, keywords in _RULES:
        for kw in keywords:
            if kw in text:
                return EmotionResult(tag=tag, tone_instruction=_TONE_MAP[tag])
    return EmotionResult(tag="neutral", tone_instruction=_TONE_MAP["neutral"])
