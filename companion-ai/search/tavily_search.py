import asyncio
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic import BaseModel

from config import config
from search.expand_query import expand_queries
from core.http_client import safe_post

logger = logging.getLogger(__name__)

_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}
# 相关 api 可文档查阅 https://docs.tavily.com/documentation/api-reference/endpoint/search
class ResultsContent(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""
    raw_content: str | None = None
    score: float | None = None
    # 增强后相关内容
    source: str = ""
    source_query: str = ""


class SearchResult(BaseModel):
    query: str = ""
    answer: str = ""
    results: list[ResultsContent] = []


class MergedSearchResult(BaseModel):
    answer: str = ""
    results: List[ResultsContent] = []



# ── Tavily 异步搜索实现 ───────────────────────────────────────────────────────────
async def tavily_search(query: str) -> str:
    if not query:
        return "[tool error] Empty search query."
    if not config.TAVILY_API_KEY:
        return "[tool error] TAVILY_API_KEY not configured."
    
    # 搜索 query 增强结果, QueryExpandResult 格式
    expanded = await expand_queries(query)
    logger.info(
        "[Tavily]] original=%r zh=%r en=%r",
        expanded.original_query,
        expanded.zh_expand_query,
        expanded.en_expand_query,
    )

    # 如果增强部分出现问题，则使用原query进行搜索
    if expanded.is_fallback:
        search_results = [
            await _call_tavily(expanded.original_query, source="ori")
        ]
    else:
        zh_result, en_result = await asyncio.gather(
            _call_tavily(expanded.zh_expand_query, source="zh"),
            _call_tavily(expanded.en_expand_query, source="en"),
        )
        search_results = [zh_result, en_result]
    
    deduped_results = _dedupe_results(search_results)

    return _format_tavily_results(deduped_results)

async def _call_tavily(query: str, source: str) -> SearchResult:
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": True,
        # 原始内容 这个可以后期在搜索内容质量优化部分进行处理，如加一个模型分析k个raw_content，给出总结
        # "include_raw_content": True,
        # 时效性限制
        "days": 7
    }

    resp = await safe_post(config.TAVILY_URL, json=payload, timeout=15.0)
    resp.raise_for_status()
    data = resp.json()

    result = SearchResult.model_validate(data)
    
    for item in result.results:
        item.source = source
        item.source_query = query

    return result


def _dedupe_results(results_list: list[SearchResult]) -> MergedSearchResult:

    def _result_rank(result: ResultsContent) -> float:                                                                                                                                                                     
        return result.score or 0.0

    merged = dict[str, ResultsContent] = {}
    answer_parts: list[str] = []

    for search_result in results_list:                                                                                                                                                                                 
        if search_result.answer:                                                                                                                                                                                       
            answer_parts.append(search_result.answer)                                                                                                                                                                  

        # 对于搜索结果根据 url 进行去重                                                                                                                                                                                                          
        for result in search_result.results:                                                                                                                                                                           
            normalized_url = _normalize_url(result.url)                                                                                                                                                                
            if not normalized_url:                                                                                                                                                                                     
                continue                                                                                                                                                                                               
                                                                                                                                                                                                                       
            existing = merged.get(normalized_url)                                                                                                                                                                      
            if existing is None:                                                                                                                                                                                       
                merged[normalized_url] = result                                                                                                                                                                        
                continue                                                                                                                                                                                               
            # 如重复 去除分数较低者                                                                                                                                                                                                       
            if _result_rank(result) > _result_rank(existing):                                                                                                                                                          
                merged[normalized_url] = result     

    # 根据每个搜索结果匹配分数重排
    sorted_results = sorted(                                                                                                                                                                                           
        merged.values(),                                                                                                                                                                                               
        key=_result_rank,                                                                                                                                                                                              
        reverse=True,                                                                                                                                                                                                  
    )                                                                                                                                                                                                                  
                                                                                                                                                                                                                       
    return MergedSearchResult(                                                                                                                                                                                         
        answer="\n".join(dict.fromkeys(answer_parts)),                                                                                                                                                                 
        results=sorted_results[:6],                                                                                                                                                                                    
    )                

def _normalize_url(url: str) -> str:                                                                                                                                                                                   
    url = (url or "").strip()                                                                                                                                                                                          
    if not url:                                                                                                                                                                                                        
        return ""                                                                                                                                                                                                      
                                                                                                                                                                                                                       
    parsed = urlsplit(url)                                                                                                                                                                                             
                                                                                                                                                                                                                       
    query_pairs = [                                                                                                                                                                                                    
        (key, value)                                                                                                                                                                                                   
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)                                                                                                                                              
        if key.lower() not in _TRACKING_PARAMS                                                                                                                                                                         
    ]                                                                                                                                                                                                                  
                                                                                                                                                                                                                       
    return urlunsplit(                                                                                                                                                                                                 
        (                                                                                                                                                                                                              
            parsed.scheme.lower(),                                                                                                                                                                                     
            parsed.netloc.lower(),                                                                                                                                                                                     
            parsed.path.rstrip("/"),                                                                                                                                                                                   
            urlencode(query_pairs),                                                                                                                                                                                    
            "",                                                                                                                                                                                                        
        )                                                                                                                                                                                                              
    )

def _format_tavily_results(data: MergedSearchResult) -> str:
    parts = []

    if data.answer:
        parts.append(f"Summary: {data.answer}")

    for i, r in enumerate(data.results, 1):
        parts.append(
            f"[{i}] {result.title}\n"
            f"URL: {result.url}\n"
            f"content: {result.content}"
        )

    if not parts:
        return "[tool error] No results found."

    return "\n\n".join(parts)