import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from config import config
from core.http_client import safe_post
from core.tool.base import BaseTool
from core.tool.tavily_search.base import TavilySearchArgs, TavilySearchResponse

logger = logging.getLogger(__name__)


class TavilySearchTool(BaseTool):
    name: str = "tavily_search"
    description: str = (
        "Search the web with Tavily for up-to-date information, source snippets, "
        "optional answer summaries, and optional content extraction."
    )
    parameters: dict = TavilySearchArgs.model_json_schema()

    async def execute(self, **kwargs) -> TavilySearchResponse:
        try:
            args = TavilySearchArgs.model_validate(kwargs)
        except Exception as exc:
            return TavilySearchResponse(error=f"Invalid arguments: {exc}")

        query = args.query.strip()
        if not query:
            return TavilySearchResponse(query=query, error="Empty search query.")

        if not config.TAVILY_API_KEY:
            return TavilySearchResponse(
                query=query, error="TAVILY_API_KEY not configured."
            )

        if args.country and args.topic != "general":
            return TavilySearchResponse(
                query=query,
                error="country is only supported when topic is general.",
            )

        if args.chunks_per_source and args.search_depth not in {"advanced"}:
            args = args.model_copy(update={"chunks_per_source": 3})

        payload: dict[str, Any] = {
            "query": query,
            "search_depth": args.search_depth,
            "chunks_per_source": args.chunks_per_source,
            "max_results": args.max_results,
            "topic": args.topic,
            "include_answer": args.include_answer,
            "include_raw_content": args.include_raw_content,
            "include_images": args.include_images,
            "include_image_descriptions": args.include_image_descriptions,
            "include_favicon": args.include_favicon,
            "include_domains": args.include_domains or None,
            "exclude_domains": args.exclude_domains or None,
            "country": args.country,
            "exact_match": args.exact_match,
            "include_usage": args.include_usage,
            "auto_parameters": args.auto_parameters,
            "safe_search": args.safe_search,
        }

        if args.time_range:
            payload["time_range"] = args.time_range
        if args.start_date:
            payload["start_date"] = args.start_date
        if args.end_date:
            payload["end_date"] = args.end_date

        payload = {k: v for k, v in payload.items() if v not in (None, [], "")}

        try:
            resp = await safe_post(
                config.TAVILY_URL,
                json=payload,
                timeout=15.0,
                headers={"Authorization": f"Bearer {config.TAVILY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return TavilySearchResponse.model_validate(
                {
                    **data,
                    "query": data.get("query", query),
                }
            )
        except Exception as exc:
            logger.exception("Tavily search failed")
            return TavilySearchResponse(query=query, error=str(exc))


async def tavily_search(query: str) -> str:
    result = await TavilySearchTool().execute(query=query)
    return result.output if not result.error else f"[tool error] {result.error}"


if __name__ == "__main__":
    result = asyncio.run(tavily_search("2026 World Cup news"))
    print(result)
