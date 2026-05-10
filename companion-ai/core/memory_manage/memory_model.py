import keyword
from pydantic import BaseModel, Field, field_validator, model_validator 
import re
from datetime import datetime
from enum import Enum


class RequestPayload(BaseModel):
    """记忆提取部分模型请求体"""
    system_prompt: str = ""
    user_content: list[dict]
    response_format: list[dict]
    temperature: float = 0.2
    top_p: float = 0.9


class MemoryQueryContext(BaseModel):
    """对话发起前用于查找用户相关信息"""
    user_id: int
    query: str
    limit: int = 6
    current_time_iso: str = ""
    timezone_name: str = "Asia/Shanghai"


class MemoryType(str, Enum):
    PROFILE = "profile"             # 用户稳定的背景资料
    PREFERENCE = "preference"       # 用户偏好习惯
    ONGOING = "ongoing"             # 持续一段时间的目标、计划、困扰、关系状态
    EVENT = "event"                 # 近期对后续对话可能重要的事件


class MemoryCandidate(BaseModel):
    """llm提取出的候选记忆"""
    memory_type: MemoryType
    content: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    # 给 LLM 用显式ISO时间
    happened_at: datetime | None = None

    @model_validator(mode="after")
    def clean_keywords(self):
        """清洗关键词内容"""
        keywords = [str(keyword).strip() for keyword in self.keywords if str(keyword).strip()]
        self.keywords = keywords
        return self

    # 在 Memory 中 confidence 被赋值的时候先进行下面的操作
    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value):
        """在类型转换之前执行对于 置信度 的数值区间限制"""
        try:
            confidence = float(value)
        except(TypeError, ValueError):
            return 0.0
        return max(0.0, min(confidence, 1.0))

class MemoryCandidateResult(BaseModel):
    """llm提取出的候选记忆列表"""
    candidates: list[MemoryCandidate] = Field(default_factory=list)

class Memory(BaseModel):
    """用于存储的长期记忆"""
    memory_type: MemoryType
    content: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    timezone_name: str = "Asia/Shanghai"
    happened_at: datetime | None = None
    # Unix时间戳
    happened_ts: int = 0

    @model_validator(mode="after")
    def get_timestamp(self):
        """生成ISO时间对应的时间戳数值"""
        if self.happened_at:
            self.happened_ts = int(self.happened_at.timestamp())

        return self

class MemoryList(BaseModel):
    """用于存储的长期记忆列表"""
    memories: list[Memory] = Field(default_factory=list)