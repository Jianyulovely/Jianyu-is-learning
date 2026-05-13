from pydantic import BaseModel, Field


# ── 请求 / 响应模型 ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """ /generate 端口请求体"""
    system_prompt: str
    user_message: str
    images: list[str] = Field(default_factory=list)      # base64 编码图片列表，无图传 []
    context: list[int] = Field(default_factory=list)     # Ollama 多轮上下文 token，首轮传 []
    response_format: dict | None = None
    max_new_tokens: int = 200
    temperature: float = 0.85
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class GenerateResponse(BaseModel):
    """ /generate 端口相应体"""
    reply: str
    context: list[int]           # 透传给调用方，存入 Redis 供下轮使用
    usage: dict


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """ /chat 端口请求体"""
    system_prompt: str
    messages: list[ChatMessage]
    images: list[str] = Field(default_factory=list)
    tools: list[dict] = Field(default_factory=list)
    response_format: dict | None = None
    temperature: float = 0.85
    top_p: float = 0.9


class ChatResponse(BaseModel):
    """ /chat 端口相应体"""
    reply: str
    tool_calls: list[dict] = Field(default_factory=list)
    usage: dict


class EmotionResult(BaseModel):
    """
    情绪分析结果 用于指导对话生成的语气控制
    tag: 用户本次消息的情绪
    tone_instruction: bot的回应情绪控制指令
    """
    tag: str
    tone_instruction: str

class SystemPromptContext(BaseModel):
    """构建 system prompt 所需的上下文"""
    role_id: str
    user_name: str
    emotion: EmotionResult
    intimacy_level: int
    image_context: str = ""
    memory_summary: str = ""
    current_time_iso: str = ""
    timezone_name: str = ""