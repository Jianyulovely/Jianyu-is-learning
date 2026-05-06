from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    PROFILE = "profile"             # 用户稳定的背景资料
    PREFERENCE = "preference"       # 用户偏好习惯
    ONGOING = "ongoing"             # 持续一段时间的目标、计划、困扰、关系状态
    EVENT = "event"                 # 近期对后续对话可能重要的事件


class Memory(BaseModel):
    memory_type: MemoryType
    content: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    happened_at: str = ""


class MemoryExtractionResult(BaseModel):
    memories: list[Memory] = Field(default_factory=list)