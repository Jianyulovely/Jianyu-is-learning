import json
from pydantic import BaseModel, ValidationError
from config import config
from core.http_client import safe_post


class PhotoDescription(BaseModel):
    scene: str
    objects: list[str]
    text_ocr: list[str]
    user_relevant_fact: list[str]

DESCRIBE_PROMPT = """
你是一个严谨的图像理解系统，请严格按照要求输出 JSON。

要求：
1. 只输出 JSON，不要任何解释
2. 字段必须完整，不可缺失
3. 如果没有内容，返回空数组 []
4. 不要编造不存在的信息

输出格式：
{
  "scene": "对图片内容的简要描述",
  "objects": ["物体1", "物体2", ...],
  "text_ocr": ["图片中出现的文字", "图片中出现的文字", ...],
  "user_relevant_fact": ["与用户本身有关的事实内容"]
}
"""

def fallback_result() -> PhotoDescription:
    return PhotoDescription(
        scene="unknown",
        objects=[],
        text_ocr=[],
        user_relevant_fact=[]
    )

def clean_json_text(text: str) -> str:
    text = text.strip()

    # 去掉 ```json ``` 包裹
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]

    return text.strip()


async def describe_image(image_b64: str) -> PhotoDescription:
    payload = {
        "system_prompt": DESCRIBE_PROMPT,
        "user_message": "开始分析这张图片",
        "images": [image_b64],
        "context": [],
        "max_new_tokens": 500,
        "temperature": 0.3,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    }
    resp = await safe_post(
        f"{config.LLM_API_URL}/generate", 
        json=payload, 
        timeout=60.0
    )
    resp.raise_for_status()

    raw_resp = (resp.json().get("reply") or "").strip()

    # 清洗
    cleaned_resp = clean_json_text(raw_resp)

    # json 解析
    try:
        data = json.loads(cleaned_resp)
    except Exception:
        return fallback_result()
    
    # pydantic 校验
    try:
        return PhotoDescription.model_validate(data)
    except ValidationError:
        return fallback_result()