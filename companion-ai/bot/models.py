from pydantic import BaseModel, Field
    

class RequestPayload(BaseModel):
    """模型请求体"""
    system_prompt: str
    history_messages: list[dict]
    images: list[str] =  Field(default_factory=list) 
    tool_context: str = ""
    temperature: float = 0.85
    top_p: float = 0.9

class ChatTurnContext(BaseModel):
    user_id: int
    user_message: str
    assistant_reply: str = ""
    image_context: str = ""
    current_time_iso: str = ""
    timezone_name: str = "Asia/Shanghai"