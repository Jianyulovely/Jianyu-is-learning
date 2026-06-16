"""
将搜索时的用户 query 内容进行扩充
同时生成中文和英文的 expand_query 内容
"""
import logging
import json
from config import config
from pydantic import BaseModel, ValidationError
from core.http_client import safe_post

logger = logging.getLogger(__name__)


class QueryExpandResult(BaseModel):
    original_query: str = ""
    zh_expand_query: str = ""
    en_expand_query: str = ""
    is_fallback: bool = False

QUERY_EXPAND_PROMPT = """
You are a search query optimization assistant.

Your task is to rewrite the user's query into better search queries in BOTH Chinese and English.

Requirements:
1. Output MUST be valid JSON, strictly following the given schema.
2. Do NOT include any explanations or extra text.
3. Keep the meaning of the original query.
4. Improve the query for search engines:
   - Make it more specific
   - Use common search phrasing
   - Add helpful keywords if necessary
5. Chinese query:
   - Natural, fluent Chinese
   - Suitable for Chinese search engines or content platforms
6. English query:
   - Use concise, information-dense phrasing
   - Prefer technical or commonly used search expressions

Output format example:
{
  "original_query": "...",
  "zh_expand_query": "...",
  "en_expand_query": "..."
}
"""


def fallback_result(ori_query) -> QueryExpandResult:
    return QueryExpandResult(
        original_query=ori_query,
        zh_expand_query="",
        en_expand_query="",
        is_fallback=True,
    )

async def expand_queries(user_query: str) -> QueryExpandResult:
    """小模型生成双语搜索 query """
    payload = {
        "model": config.QUERY_EXPAND_MODEL,
        "system": QUERY_EXPAND_PROMPT,
        "prompt": user_query,
        "stream": False,
        "format": QueryExpandResult.model_json_schema(),
        "options": {"temperature": 0.0},
    }
    try:
        resp = await safe_post(
            config.OLLAMA_GEN_URL,
            json=payload,
        )
        resp.raise_for_status()

        content = (resp.json().get("response", "")).strip()
        cleaned = clean_json_text(content)
        parsed = json.loads(cleaned)
        # pydantic 校验
        expand_query = QueryExpandResult.model_validate(parsed)

        return expand_query

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"[query_expand] parse failed ({e}), fallback and using original query: {user_query}")
        return fallback_result(user_query)

    except Exception as e:
        logger.warning(f"[query_expand] failed ({e}), fallback and using original query: {user_query}")
        return fallback_result(user_query)


def clean_json_text(text: str) -> str:
    text = text.strip()

    # 处理 ```xxx ... ``` 包裹
    if text.startswith("```"):
        lines = text.splitlines()

        # 去掉第一行 ```json / ```JSON / ```
        first_line = lines[0].strip().lower()
        if first_line.startswith("```"):
            lines = lines[1:]

        # 去掉最后一行 ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return text