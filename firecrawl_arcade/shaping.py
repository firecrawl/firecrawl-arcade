"""Response shapers: flatten Firecrawl SDK objects into TypedDict outputs."""

from __future__ import annotations

from typing import Any

from firecrawl_arcade.constants import MAX_DESCRIPTION_CHARS, MAX_MARKDOWN_CHARS, truncate
from firecrawl_arcade.models.outputs import (
    CrawlDocumentItem,
    DeveloperSearchHit,
    GithubIssueItem,
    MapLinkItem,
    ResearchPaperItem,
    SearchResultItem,
)


def _meta_get(doc: Any, key: str) -> Any:
    meta = getattr(doc, "metadata", None)
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta.get(key)
    return getattr(meta, key, None)


def shape_scrape_document(doc: Any, fallback_url: str = "") -> dict[str, Any]:
    url = _meta_get(doc, "url") or fallback_url
    return {
        "url": url or "",
        "title": _meta_get(doc, "title"),
        "description": truncate(_meta_get(doc, "description"), MAX_DESCRIPTION_CHARS),
        "markdown": truncate(getattr(doc, "markdown", None), MAX_MARKDOWN_CHARS),
        "html": truncate(getattr(doc, "html", None), MAX_MARKDOWN_CHARS),
        "links": getattr(doc, "links", None),
        "screenshot": getattr(doc, "screenshot", None),
        "summary": truncate(getattr(doc, "summary", None), MAX_DESCRIPTION_CHARS),
        "warning": getattr(doc, "warning", None),
    }


def shape_search_item(item: Any) -> SearchResultItem:
    if hasattr(item, "markdown"):
        # Document from scrapeOptions
        return SearchResultItem(
            url=_meta_get(item, "url") or getattr(item, "url", "") or "",
            title=_meta_get(item, "title") or getattr(item, "title", None),
            description=truncate(
                _meta_get(item, "description") or getattr(item, "description", None),
                MAX_DESCRIPTION_CHARS,
            ),
            markdown=truncate(getattr(item, "markdown", None), MAX_MARKDOWN_CHARS),
            position=getattr(item, "position", None),
        )
    return SearchResultItem(
        url=getattr(item, "url", "") or "",
        title=getattr(item, "title", None),
        description=truncate(getattr(item, "description", None), MAX_DESCRIPTION_CHARS),
        markdown=None,
        position=getattr(item, "position", None),
    )


def shape_map_link(item: Any) -> MapLinkItem:
    if isinstance(item, str):
        return MapLinkItem(url=item, title=None, description=None)
    return MapLinkItem(
        url=getattr(item, "url", "") or "",
        title=getattr(item, "title", None),
        description=truncate(getattr(item, "description", None), MAX_DESCRIPTION_CHARS),
    )


def shape_crawl_document(doc: Any) -> CrawlDocumentItem:
    return CrawlDocumentItem(
        url=_meta_get(doc, "url") or "",
        title=_meta_get(doc, "title"),
        markdown=truncate(getattr(doc, "markdown", None), MAX_MARKDOWN_CHARS),
    )


def shape_developer_hit(item: Any) -> DeveloperSearchHit:
    if isinstance(item, dict):
        passages_raw = item.get("passages") or item.get("evidence") or []
        passages: list[str] = []
        for p in passages_raw:
            if isinstance(p, str):
                passages.append(truncate(p, MAX_DESCRIPTION_CHARS) or "")
            elif isinstance(p, dict):
                passages.append(
                    truncate(p.get("text") or p.get("content") or str(p), MAX_DESCRIPTION_CHARS)
                    or ""
                )
        return DeveloperSearchHit(
            title=item.get("title"),
            url=item.get("url") or item.get("html_url"),
            type=item.get("type") or item.get("kind"),
            repo=item.get("repo") or item.get("repository"),
            score=item.get("score"),
            passages=passages,
        )
    return DeveloperSearchHit(
        title=getattr(item, "title", None),
        url=getattr(item, "url", None),
        type=getattr(item, "type", None),
        repo=getattr(item, "repo", None),
        score=getattr(item, "score", None),
        passages=[],
    )


def shape_paper(item: Any, inspect_meta: dict[str, Any] | None = None) -> ResearchPaperItem:
    data = item if isinstance(item, dict) else {}
    if not isinstance(item, dict):
        data = {
            "paperId": getattr(item, "paper_id", None) or getattr(item, "paperId", None),
            "title": getattr(item, "title", None),
            "abstract": getattr(item, "abstract", None),
            "authors": getattr(item, "authors", None),
            "year": getattr(item, "year", None),
            "url": getattr(item, "url", None),
            "source": getattr(item, "source", None),
        }

    paper_id = data.get("paperId") or data.get("paper_id") or data.get("primaryId") or ""
    authors = data.get("authors") or []
    if authors and isinstance(authors[0], dict):
        authors = [a.get("name") or a.get("fullName") or str(a) for a in authors]

    meta = inspect_meta or {}
    return ResearchPaperItem(
        paper_id=str(paper_id),
        title=data.get("title"),
        abstract=truncate(data.get("abstract") or data.get("summary"), MAX_MARKDOWN_CHARS),
        authors=[str(a) for a in authors] if isinstance(authors, list) else [],
        year=data.get("year") or data.get("publicationYear"),
        url=data.get("url") or data.get("pdfUrl"),
        source=data.get("source") or data.get("venue"),
        citation_count=meta.get("citationCount") or meta.get("citation_count") or data.get("citationCount"),
        categories=meta.get("categories") or data.get("categories"),
    )


def shape_github_issue(item: Any) -> GithubIssueItem:
    if isinstance(item, dict):
        body = item.get("body") or item.get("body_excerpt") or item.get("snippet")
        return GithubIssueItem(
            title=item.get("title"),
            url=item.get("url") or item.get("html_url"),
            repo=item.get("repo") or item.get("repository"),
            state=item.get("state"),
            number=item.get("number"),
            body_excerpt=truncate(body, MAX_DESCRIPTION_CHARS),
        )
    return GithubIssueItem(
        title=getattr(item, "title", None),
        url=getattr(item, "url", None),
        repo=getattr(item, "repo", None),
        state=getattr(item, "state", None),
        number=getattr(item, "number", None),
        body_excerpt=truncate(getattr(item, "body", None), MAX_DESCRIPTION_CHARS),
    )
