from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Literal

from core.tool.base import ToolResult


class TavilyImage(BaseModel):
    url: str = ""
    description: str = ""


class TavilyResultItem(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""
    score: float | None = None
    raw_content: str | None = None

    favicon: str | None = None # 网站图标
    images: list[TavilyImage] = Field(default_factory=list)


class TavilySearchArgs(BaseModel):
    query: str = Field(description="The search query to execute with Tavily.")
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = Field(
        default="basic",
        description="Controls the latency vs. relevance tradeoff.",
    )
    chunks_per_source: int = Field(
        default=3,
        ge=1,
        le=3,
        description="Maximum number of relevant chunks per source.",
    )
    max_results: int = Field(
        default=5,
        ge=0,
        le=20,
        description="The maximum number of search results to return.",
    )
    topic: Literal["general", "news", "finance"] = Field(
        default="general",
        description="The category of the search.",
    )
    time_range: Optional[Literal["day", "week", "month", "year", "d", "w", "m", "y"]] = Field(
        default=None,
        description="Filter results by publish or update time range.",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Return results after this date in YYYY-MM-DD format.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Return results before this date in YYYY-MM-DD format.",
    )
    include_answer: bool = Field(default=False, description="Include an answer.")
    include_raw_content: bool = Field(
        default=False, description="Include cleaned and parsed result content."
    )
    include_images: bool = Field(default=False, description="Include images.")
    include_image_descriptions: bool = Field(
        default=False, description="Include image descriptions."
    )
    include_favicon: bool = Field(default=False, description="Include favicon URLs.")
    include_domains: list[str] = Field(
        default_factory=list,
        description="Domains to specifically include in the search results.",
    )
    exclude_domains: list[str] = Field(
        default_factory=list,
        description="Domains to specifically exclude from the search results.",
    )
    country: Optional[str] = Field(
        default=None,
        description="Country boost for general topic searches.",
    )
    exact_match: bool = Field(
        default=False,
        description="Return only results containing the exact quoted phrase(s).",
    )
    include_usage: bool = Field(
        default=False, description="Include credit usage information."
    )
    auto_parameters: bool = Field(
        default=False,
        description="Let Tavily automatically configure search parameters.",
    )
    safe_search: bool = Field(
        default=False, description="Filter adult or unsafe content."
    )


class TavilySearchResponse(ToolResult):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str = ""
    answer: str | None = None
    images: list[TavilyImage] = Field(default_factory=list)
    results: list[TavilyResultItem] = Field(default_factory=list)
    response_time: float | None = None
    auto_parameters: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""

    @model_validator(mode="after")
    def populate_output(self) -> "TavilySearchResponse":
        if self.error:
            return self

        parts: list[str] = [f"Query: {self.query}"]

        if self.answer:
            parts.append(f"Answer: {self.answer}")

        for i, result in enumerate(self.results, 1):
            lines = [f"[{i}] {result.title or 'No title'}", f"URL: {result.url}"]
            if content := result.content:
                preview = content[:1000].replace("\n", " ").strip()
                lines.append(f"Content: {preview}{'...' if len(content) > 1000 else ''}")

            if r_content := result.raw_content:
                r_preview = r_content[:1000].replace("\n", " ").strip()
                lines.append(f"Raw: {r_preview}{'...' if len(r_content) > 1000 else ''}")

            if result.favicon:
                lines.append(f"Favicon: {result.favicon}")
            if result.score is not None:
                lines.append(f"Score: {result.score}")
            parts.append("\n".join(lines))

        if self.images:
            parts.append(f"Images: {len(self.images)}")

        if self.response_time is not None:
            parts.append(f"Response time: {self.response_time}")

        if self.auto_parameters:
            parts.append(f"Auto parameters: {self.auto_parameters}")

        if self.usage:
            parts.append(f"Usage: {self.usage}")

        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")

        self.output = "\n\n".join(parts)
        return self
