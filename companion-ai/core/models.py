from pydantic import BaseModel


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