from pydantic import BaseModel, Field, field_validator, model_validator 
from datetime import date, datetime
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
    current_time: datetime | None = None
    current_time_iso: str = ""

    @model_validator(mode="after")
    def parse_current_time(self):
        """
        根据ISO字符串生成实际时间，这里的ISO字符串代表query发起时间，一定会产生
        这样就不用来回传timezone了
        """
        if self.current_time_iso:
            self.current_time = datetime.fromisoformat(self.current_time_iso)

        return self


class MemoryType(str, Enum):
    """四种记忆类型"""
    PROFILE = "profile"             # 用户稳定的背景资料
    PREFERENCE = "preference"       # 用户偏好习惯
    ONGOING = "ongoing"             # 持续一段时间的目标、计划、困扰、关系状态
    EVENT = "event"                 # 近期对后续对话可能重要的事件


class MemoryBase(BaseModel):
    """记忆类型基类"""
    memory_type: MemoryType
    content: str = ""
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    # 在 confidence 被赋值的时候先进行下面区间限制操作（0-1）
    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value):
        """在类型转换之前执行对于 置信度 的数值区间限制"""
        try:
            confidence = float(value)
        except(TypeError, ValueError):
            return 0.0
        return max(0.0, min(confidence, 1.0))

    @model_validator(mode="after")
    def clean_keywords(self):
        """清洗关键词内容"""
        keywords = [str(keyword).strip() for keyword in self.keywords if str(keyword).strip()]
        self.keywords = keywords
        return self
    

class MemoryCandidate(MemoryBase):
    """llm提取出的候选记忆"""
    # 给 LLM 用显式ISO时间
    happened_at: datetime | None = None

    # 防止由llm生成的 happened_at 是空字符串从而验证错误
    @field_validator("happened_at", mode="before")
    @classmethod
    def empty_happened_at_to_none(cls, value):
        if not value:
            return None
        return value

class MemoryCandidateResult(BaseModel):
    """llm提取出的候选记忆列表"""
    memories: list[MemoryCandidate] = Field(default_factory=list)

class Memory(MemoryBase):
    """用于存储的一份长期记忆"""
    keywords: list[str] = Field(default_factory=list)
    timezone_name: str = "Asia/Shanghai"
    # 具体年月日时间
    happened_at: datetime | None = None
    # Unix时间戳
    happened_ts: int | None = None

    @model_validator(mode="after")
    def get_timestamp(self):
        """生成ISO时间对应的时间戳数值"""
        if self.happened_at:
            self.happened_ts = int(self.happened_at.timestamp())

        return self

class MemoryList(BaseModel):
    """用于存储的长期记忆列表"""
    memories: list[Memory] = Field(default_factory=list)


class ExistingMemory(BaseModel):
    """数据库中已有记忆类型 用于记忆更新时查找"""
    id: int
    memory_type: MemoryType
    content: str = ""
    # 关键词列表存入数据库时为字符串
    keywords_json: str = ""
    confidence: float = 0.0
    # Unix时间戳 
    happened_at: int | None = None  


class ActiveMemory(BaseModel):
    """从数据库中获取的 active 长期记忆"""
    user_id: int
    memory_type: MemoryType
    content: str = ""
    happened_at_iso: str = ""
    updated_at_iso: str = ""
    last_seen_at_iso: str = ""

class ActiveMemoryList(BaseModel):
    """从数据库中获取的 active 长期记忆列表"""
    memories: list[ActiveMemory] = Field(default_factory=list)


class MemorySummary(BaseModel):
    """根据用户 query 获取到的长期记忆内容"""
    preference: str = ""
    profile: str = ""
    ongoing: str = ""
    event: str = ""