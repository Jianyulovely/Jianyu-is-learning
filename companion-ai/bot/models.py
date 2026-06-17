from pydantic import BaseModel, Field
    

class RequestPayload(BaseModel):
    """模型请求体"""
    system_prompt: str
    history_messages: list[dict]
    images: list[str] =  Field(default_factory=list) 
    tool_context: str = ""
    tools: list[dict] = Field(default_factory=list)
    response_format: dict | None = None
    temperature: float = 0.85
    top_p: float = 0.9

class ChatTurnContext(BaseModel):
    """一轮对话内容结构"""
    user_id: int
    user_message: str
    assistant_reply: str = ""
    image_context: str = ""
    # 对话发生时间
    current_time_iso: str = ""
    timezone_name: str = "Asia/Shanghai"
