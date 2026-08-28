#!/usr/bin/env python3
"""Live smoke test against a real FIRECRAWL_API_KEY.

Exercises all 12 Arcade tool functions end to end.

Usage:
  export FIRECRAWL_API_KEY=fc-...
  uv run python scripts/smoke_live.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


async def main() -> int:
    _load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if not os.environ.get("FIRECRAWL_API_KEY"):
        print("FIRECRAWL_API_KEY is not set; skip live smoke.", file=sys.stderr)
        return 2

    for key in list(os.environ):
        if "proxy" in key.lower():
            os.environ.pop(key, None)

    from firecrawl_arcade.tools import research, web

    class Ctx:
        def get_secret(self, name: str) -> str:
            value = os.environ.get(name)
            if not value:
                raise KeyError(name)
            return value

    ctx = Ctx()
    results: list[tuple[str, str]] = []

    scrape = await web.scrape_url(ctx, url="https://example.com")
    results.append(("ScrapeUrl", f"md={len(scrape.get('markdown') or '')}"))

    search = await web.search(ctx, query="firecrawl scrape api", limit=2)
    results.append(("Search", f"count={search.get('result_count')}"))

    mapped = await web.map_website(ctx, url="https://example.com", limit=5)
    results.append(("MapWebsite", f"links={mapped.get('link_count')}"))

    crawl = await web.crawl_website(
        ctx, url="https://example.com", limit=2, wait_seconds=30
    )
    results.append(
        ("CrawlWebsite", f"status={crawl.get('status')} job={crawl.get('job_id')}")
    )
    job_id = crawl.get("job_id") or ""
    if job_id:
        status = await web.get_crawl_status(ctx, job_id=job_id)
        results.append(("GetCrawlStatus", f"status={status.get('status')}"))
        data = await web.get_crawl_data(ctx, job_id=job_id)
        results.append(("GetCrawlData", f"docs={len(data.get('data') or [])}"))
        try:
            cancel = await web.cancel_crawl(ctx, job_id=job_id)
            results.append(("CancelCrawl", f"cancelled={cancel.get('cancelled')}"))
        except Exception as exc:  # noqa: BLE001
            results.append(("CancelCrawl", f"{type(exc).__name__}:{str(exc)[:80]}"))

    extract = await web.extract_data(
        ctx,
        prompt="Extract the page title",
        urls=["https://example.com"],
        wait_seconds=45,
    )
    results.append(
        (
            "ExtractData",
            f"status={extract.get('status')} job={extract.get('job_id')} data={bool(extract.get('data_json'))}",
        )
    )
    if extract.get("job_id"):
        est = await web.get_extract_status(ctx, job_id=extract["job_id"])
        results.append(("GetExtractStatus", f"status={est.get('status')}"))

    docs = await research.search_developer_docs(
        ctx, query="firecrawl scrape timeout", k=2
    )
    results.append(("SearchDeveloperDocs", f"count={docs.get('result_count')}"))

    papers = await research.search_research_papers(
        ctx, query="web scraping LLM", k=2, include_inspect=False
    )
    results.append(("SearchResearchPapers", f"count={papers.get('result_count')}"))

    issues = await research.search_github_issues(
        ctx, query="firecrawl rate limit", k=2
    )
    results.append(("SearchGithubIssues", f"count={issues.get('result_count')}"))

    for name, detail in results:
        print(f"{name}: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
