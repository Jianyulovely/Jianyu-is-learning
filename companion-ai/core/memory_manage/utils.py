import json
import re                                                                                                                                                              
import logging 
from typing import TypeVar, Type 
from pydantic import BaseModel

def decode_keywords(keywords_json: str) -> list[str]:
    """将字符串转换为字符串列表"""
    try:
        data = json.loads(keywords_json or "[]")
    except json.JSONDecodeError:
        return []
    results: list[str] = []
    for item in data:
        token = str(item).strip().lower()
        if token and token not in results:
            results.append(token)
    return results

def merge_keywords(exist_kw: list[str], new_kw: list[str]) -> list[str]:
    """更新相关记忆中的关键词内容"""
    merged: list[str] = []
    for token in exist_kw + new_kw:
        normalized = str(token).strip().lower()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged

T = TypeVar("T", bound=BaseModel) 
def parse_llm_json_result(
    raw: str,
    model_cls: Type[T], # 传进来的 Pydantic 模型类
    logger: logging.Logger
) -> T:
    """模型返回json内容解析函数"""
    default = model_cls()
    if not raw:
        return default
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 从原始返回结果中找出json的标志性的前后大括号
        # 其中的内容就是正确的返回结果
        match = re.search(r"\{.*\}", raw, re.S)
        # 返回结果不是标准json
        if not match:
            logger.warning("memory extractor returned non-json: %r", raw[:100])
            return default
        
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("memory extractor json parse failed: %r", raw[:100])
            return default
    try:
        return model_cls.model_validate(data)
        
    except Exception as exc:
        logger.warning("memory extractor schema validation failed: %s", exc)
        return default