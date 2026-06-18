from pydantic import BaseModel, Field

from config import config


class RequestPayload(BaseModel):
    """模型请求体"""
    system_prompt: str
    history_messages: list[dict]
    images: list[str] = Field(default_factory=list)
    tool_context: str = ""
    tools: list[dict] = Field(default_factory=list)
    response_format: dict | None = None
    temperature: float | None = config.LLM_TEMPERATURE
    top_p: float | None = config.LLM_TOP_P
    # 强制 LLM 一轮只发一个 tool_call，避免并行 tool_calls 在 waiting_human 时
    # 出现 tool response 缺位、协议 400（AUDIT P-02）
    parallel_tool_calls: bool = False


class ChatTurnContext(BaseModel):
    """一轮对话内容"""
    user_id: int
    user_message: str
    assistant_reply: str = ""
    image_context: str = ""
    current_time_iso: str = ""
    timezone_name: str = "Asia/Shanghai"
