"""Web tools: scrape, search, map, crawl, extract."""

import asyncio
import json
import time
from typing import Annotated, Optional

from arcade_mcp_server import Context, tool
from arcade_tdk.errors import RetryableToolError


from firecrawl_arcade.client import get_firecrawl_client
from firecrawl_arcade.constants import (
    CRAWL_WAIT_BUDGET_SECONDS,
    DEFAULT_CRAWL_LIMIT,
    DEFAULT_MAP_LIMIT,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_SEARCH_LIMIT,
    EXTRACT_WAIT_BUDGET_SECONDS,
    MAX_CRAWL_LIMIT,
    MAX_MAP_LIMIT,
    MAX_SEARCH_LIMIT,
    MIN_LIMIT,
    clamp,
)
from firecrawl_arcade.errors import FIRECRAWL_ADAPTERS
from firecrawl_arcade.metadata import CANCEL_METADATA, READ_METADATA
from firecrawl_arcade.models.enums import (
    AgentEffort,
    AgentModel,
    OutputFormat,
    ProxyMode,
    SearchCategory,
    SearchSource,
    SitemapMode,
)
from firecrawl_arcade.models.outputs import (
    CancelCrawlOutput,
    CrawlDataOutput,
    CrawlStatusOutput,
    CrawlWebsiteOutput,
    ExtractDataOutput,
    ExtractStatusOutput,
    MapWebsiteOutput,
    ScrapeUrlOutput,
    SearchOutput,
)
from firecrawl_arcade.shaping import (
    shape_crawl_document,
    shape_map_link,
    shape_scrape_document,
    shape_search_item,
)

_SECRET = ["FIRECRAWL_API_KEY"]


@tool(
    name="ScrapeUrl",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def scrape_url(
    context: Context,
    url: Annotated[str, "Absolute URL to scrape (http or https)"],
    formats: Annotated[
        Optional[list[OutputFormat]],
        "Output formats to return. Defaults to markdown only.",
    ] = None,
    only_main_content: Annotated[
        bool,
        "If true, exclude navs, footers, and sidebars from the content.",
    ] = True,
    proxy: Annotated[
        Optional[ProxyMode],
        "Proxy mode: basic, stealth, enhanced, or auto. Leave unset for Firecrawl default.",
    ] = None,
) -> Annotated[ScrapeUrlOutput, "Scraped page content and metadata"]:
    """Scrape a single URL and return LLM-ready content (markdown by default).

    Use for one known page. Prefer Search to find pages, MapWebsite to list
    site URLs, CrawlWebsite for multi-page collection, ExtractData for
    structured fields across unknown pages.
    """
    if not url.startswith(("http://", "https://")):
        raise RetryableToolError(
            message=f"Invalid URL '{url}'. Provide an absolute http(s) URL.",
            developer_message=f"url={url!r} failed scheme check",
            additional_prompt_content=(
                "Pass a full URL like https://example.com/pricing. "
                "Relative paths and bare domains without a scheme are rejected."
            ),
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    format_values = [f.value for f in formats] if formats else ["markdown"]
    kwargs: dict = {
        "formats": format_values,
        "only_main_content": only_main_content,
    }
    if proxy is not None:
        kwargs["proxy"] = proxy.value

    doc = await client.scrape(url, **kwargs)
    return ScrapeUrlOutput(**shape_scrape_document(doc, fallback_url=url))


@tool(
    name="Search",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def search(
    context: Context,
    query: Annotated[str, "Web search query"],
    limit: Annotated[
        int,
        f"Max results to return (min {MIN_LIMIT}, max {MAX_SEARCH_LIMIT})",
    ] = DEFAULT_SEARCH_LIMIT,
    sources: Annotated[
        Optional[list[SearchSource]],
        "Result sources to include: web, news, images. Defaults to web.",
    ] = None,
    categories: Annotated[
        Optional[list[SearchCategory]],
        "Optional category filters: github, research (academic sites), pdf, developer.",
    ] = None,
    scrape_content: Annotated[
        bool,
        "If true (default), also scrape each result page to markdown in one call.",
    ] = True,
    location: Annotated[
        Optional[str],
        "Optional location bias for search results (e.g. 'San Francisco, California, United States').",
    ] = None,
) -> Annotated[SearchOutput, "Search results, optionally with scraped page content"]:
    """Search the web and optionally scrape each result into markdown in one call.

    Prefer this over ScrapeUrl when the URL is unknown. Prefer SearchResearchPapers
    for scientific literature and SearchDeveloperDocs for code/docs indexes.
    """
    client = get_firecrawl_client(context)
    limit = clamp(limit, MIN_LIMIT, MAX_SEARCH_LIMIT)
    source_values = [s.value for s in sources] if sources else ["web"]
    kwargs: dict = {
        "limit": limit,
        "sources": source_values,
    }
    if categories:
        kwargs["categories"] = [c.value for c in categories]
    if location:
        kwargs["location"] = location
    if scrape_content:
        kwargs["scrape_options"] = {"formats": ["markdown"], "only_main_content": True}

    data = await client.search(query, **kwargs)
    web = [shape_search_item(i) for i in (data.web or [])]
    news = [shape_search_item(i) for i in (data.news or [])]
    images = [shape_search_item(i) for i in (data.images or [])]
    return SearchOutput(
        query=query,
        web=web,
        news=news,
        images=images,
        result_count=len(web) + len(news) + len(images),
    )


@tool(
    name="MapWebsite",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def map_website(
    context: Context,
    url: Annotated[str, "Site URL to map (homepage or section root)"],
    search: Annotated[
        Optional[str],
        "Optional keyword filter; only return links related to this term.",
    ] = None,
    limit: Annotated[
        int,
        f"Max URLs to return (min {MIN_LIMIT}, max {MAX_MAP_LIMIT})",
    ] = DEFAULT_MAP_LIMIT,
    include_subdomains: Annotated[bool, "Include subdomains in the map."] = False,
    sitemap: Annotated[
        SitemapMode,
        "Sitemap handling: include, skip, or only.",
    ] = SitemapMode.INCLUDE,
) -> Annotated[MapWebsiteOutput, "Discovered URLs for the website"]:
    """Discover URLs on a website from a single starting URL (site map).

    Returns links only, not page content. Use CrawlWebsite to fetch content for
    many pages, or ScrapeUrl for one page.
    """
    if not url.startswith(("http://", "https://")):
        raise RetryableToolError(
            message=f"Invalid URL '{url}'. Provide an absolute http(s) URL.",
            developer_message=f"url={url!r} failed scheme check",
            additional_prompt_content="Pass a full URL like https://docs.example.com.",
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    limit = clamp(limit, MIN_LIMIT, MAX_MAP_LIMIT)
    result = await client.map(
        url,
        search=search,
        limit=limit,
        include_subdomains=include_subdomains,
        sitemap=sitemap.value,
    )
    links = [shape_map_link(item) for item in (result.links or [])]
    return MapWebsiteOutput(url=url, links=links, link_count=len(links))


@tool(
    name="CrawlWebsite",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def crawl_website(
    context: Context,
    url: Annotated[str, "Starting URL for the crawl"],
    limit: Annotated[
        int,
        f"Max pages to crawl (min {MIN_LIMIT}, max {MAX_CRAWL_LIMIT})",
    ] = DEFAULT_CRAWL_LIMIT,
    max_discovery_depth: Annotated[
        Optional[int],
        "Max link-following depth from the start URL. Leave unset for Firecrawl default.",
    ] = None,
    sitemap: Annotated[
        SitemapMode,
        "Sitemap handling: include, skip, or only.",
    ] = SitemapMode.INCLUDE,
    wait_seconds: Annotated[
        int,
        f"Seconds to wait for completion before returning a job id (default {CRAWL_WAIT_BUDGET_SECONDS}).",
    ] = CRAWL_WAIT_BUDGET_SECONDS,
) -> Annotated[CrawlWebsiteOutput, "Crawl results or a job id if still running"]:
    """Crawl a website and return page markdown for each discovered URL.

    Waits up to wait_seconds. If the crawl is still running, returns job_id plus
    next_action_hint so you can poll with GetCrawlStatus / GetCrawlData.
    """
    if not url.startswith(("http://", "https://")):
        raise RetryableToolError(
            message=f"Invalid URL '{url}'. Provide an absolute http(s) URL.",
            developer_message=f"url={url!r} failed scheme check",
            additional_prompt_content="Pass a full URL like https://docs.example.com.",
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    limit = clamp(limit, MIN_LIMIT, MAX_CRAWL_LIMIT)
    wait_seconds = clamp(wait_seconds, 5, 180)

    start_kwargs: dict = {
        "limit": limit,
        "sitemap": sitemap.value,
        "scrape_options": {"formats": ["markdown"], "only_main_content": True},
    }
    if max_discovery_depth is not None:
        start_kwargs["max_discovery_depth"] = max(0, max_discovery_depth)

    started = await client.start_crawl(url, **start_kwargs)
    job_id = started.id

    try:
        job = await client.wait_crawl(
            job_id,
            poll_interval=DEFAULT_POLL_INTERVAL_SECONDS,
            timeout=wait_seconds,
        )
    except TimeoutError:
        return CrawlWebsiteOutput(
            job_id=job_id,
            status="scraping",
            completed=0,
            total=0,
            credits_used=0,
            data=[],
            next_action_hint=(
                f"Crawl {job_id} is still running. Call GetCrawlStatus to check progress, "
                "GetCrawlData when completed, or CancelCrawl to stop it."
            ),
        )

    docs = [shape_crawl_document(d) for d in (job.data or [])]
    hint = None
    if job.status != "completed":
        hint = (
            f"Crawl finished with status={job.status}. "
            "Call GetCrawlData for any partial results or start a new crawl."
        )
    return CrawlWebsiteOutput(
        job_id=job_id,
        status=job.status,
        completed=job.completed,
        total=job.total,
        credits_used=job.credits_used,
        data=docs,
        next_action_hint=hint,
    )


@tool(
    name="GetCrawlStatus",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def get_crawl_status(
    context: Context,
    job_id: Annotated[str, "Crawl job id returned by CrawlWebsite"],
) -> Annotated[CrawlStatusOutput, "Current crawl job status"]:
    """Get the status of a Firecrawl crawl job (in progress or finished)."""
    client = get_firecrawl_client(context)
    job = await client.get_crawl_status(job_id)
    hint = None
    if job.status == "scraping":
        hint = "Still running. Call GetCrawlStatus again shortly, or GetCrawlData when completed."
    elif job.status == "completed":
        hint = "Completed. Call GetCrawlData to retrieve page content."
    return CrawlStatusOutput(
        job_id=job_id,
        status=job.status,
        completed=job.completed,
        total=job.total,
        credits_used=job.credits_used,
        next_action_hint=hint,
    )


@tool(
    name="GetCrawlData",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def get_crawl_data(
    context: Context,
    job_id: Annotated[str, "Crawl job id returned by CrawlWebsite"],
) -> Annotated[CrawlDataOutput, "Crawl page data for a job"]:
    """Get scraped page data for a Firecrawl crawl job."""
    client = get_firecrawl_client(context)
    job = await client.get_crawl_status(job_id)
    docs = [shape_crawl_document(d) for d in (job.data or [])]
    hint = None
    if job.status == "scraping":
        hint = "Crawl still running; returned data may be partial. Poll again soon."
    return CrawlDataOutput(
        job_id=job_id,
        status=job.status,
        completed=job.completed,
        total=job.total,
        data=docs,
        next_action_hint=hint,
    )


@tool(
    name="CancelCrawl",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=CANCEL_METADATA,
)
async def cancel_crawl(
    context: Context,
    job_id: Annotated[str, "Crawl job id to cancel"],
) -> Annotated[CancelCrawlOutput, "Whether the crawl was cancelled"]:
    """Cancel an in-progress Firecrawl crawl job."""
    client = get_firecrawl_client(context)
    try:
        cancelled = await client.cancel_crawl(job_id)
        return CancelCrawlOutput(job_id=job_id, cancelled=bool(cancelled))
    except Exception as exc:
        # 409 means the crawl already finished; treat as successfully settled.
        status = getattr(exc, "status_code", None)
        message = str(exc).lower()
        if status == 409 or "already completed" in message or "status code 409" in message:
            return CancelCrawlOutput(job_id=job_id, cancelled=True)
        raise


@tool(
    name="ExtractData",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def extract_data(
    context: Context,
    prompt: Annotated[
        str,
        "Natural-language description of the data to extract (e.g. 'all product names and prices').",
    ],
    urls: Annotated[
        Optional[list[str]],
        "Optional seed URLs. If omitted, the agent searches the web for sources.",
    ] = None,
    model: Annotated[
        AgentModel,
        "Agent model: spark-1-mini (fast), spark-1-pro, or spark-2.",
    ] = AgentModel.SPARK_1_MINI,
    effort: Annotated[
        Optional[AgentEffort],
        "Optional reasoning effort: low, medium, high.",
    ] = None,
    wait_seconds: Annotated[
        int,
        f"Seconds to wait for completion before returning a job id (default {EXTRACT_WAIT_BUDGET_SECONDS}).",
    ] = EXTRACT_WAIT_BUDGET_SECONDS,
) -> Annotated[ExtractDataOutput, "Extracted structured data or a job id if still running"]:
    """Autonomously gather structured data from the web with a single prompt.

    Use when the goal is fields/records (products, prices, contacts), not raw
    page markdown. Waits up to wait_seconds; on overrun returns job_id and
    next_action_hint for GetExtractStatus.
    """
    if not prompt.strip():
        raise RetryableToolError(
            message="prompt must be a non-empty description of the data to extract.",
            developer_message="empty prompt",
            additional_prompt_content=(
                "Describe the data, e.g. 'Extract every product name, price, and "
                "availability from this store.'"
            ),
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    wait_seconds = clamp(wait_seconds, 10, 300)
    start_kwargs: dict = {
        "prompt": prompt,
        "model": model.value,
    }
    if urls:
        start_kwargs["urls"] = urls
    if effort is not None:
        start_kwargs["effort"] = effort.value

    started = await client.start_agent(**start_kwargs)
    job_id = started.id or ""

    deadline = time.monotonic() + wait_seconds
    while True:
        status = await client.get_agent_status(job_id)
        if status.status in ("completed", "failed"):
            hint = None
            if status.status == "failed":
                hint = (
                    "Extraction failed. Inspect error and retry with a clearer "
                    "prompt or fewer URLs."
                )
            return ExtractDataOutput(
                job_id=job_id,
                status=status.status or "unknown",
                data_json=_to_json(status.data),
                error=status.error,
                credits_used=status.credits_used,
                model=status.model,
                next_action_hint=hint,
            )
        if time.monotonic() >= deadline:
            return ExtractDataOutput(
                job_id=job_id,
                status=status.status or "processing",
                data_json=None,
                error=None,
                credits_used=status.credits_used,
                model=status.model,
                next_action_hint=(
                    f"Extraction job {job_id} is still running. "
                    "Call GetExtractStatus to poll for results."
                ),
            )
        await asyncio.sleep(DEFAULT_POLL_INTERVAL_SECONDS)


@tool(
    name="GetExtractStatus",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def get_extract_status(
    context: Context,
    job_id: Annotated[str, "Extract/agent job id returned by ExtractData"],
) -> Annotated[ExtractStatusOutput, "Current extract job status and data"]:
    """Poll an ExtractData (agent) job for status and results."""
    client = get_firecrawl_client(context)
    status = await client.get_agent_status(job_id)
    hint = None
    if status.status == "processing":
        hint = "Still running. Call GetExtractStatus again shortly."
    return ExtractStatusOutput(
        job_id=job_id,
        status=status.status or "unknown",
        data_json=_to_json(status.data),
        error=status.error,
        credits_used=status.credits_used,
        next_action_hint=hint,
    )


def _to_json(value: object) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(value, default=str)
    except TypeError:
        return json.dumps(str(value))
