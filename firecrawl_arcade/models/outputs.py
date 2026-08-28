"""TypedDict output shapes for Firecrawl Arcade tools."""

from typing import Optional, TypedDict


class ScrapeUrlOutput(TypedDict, total=False):
    url: str
    title: Optional[str]
    description: Optional[str]
    markdown: Optional[str]
    html: Optional[str]
    links: Optional[list[str]]
    screenshot: Optional[str]
    summary: Optional[str]
    warning: Optional[str]


class SearchResultItem(TypedDict, total=False):
    url: str
    title: Optional[str]
    description: Optional[str]
    markdown: Optional[str]
    position: Optional[int]


class SearchOutput(TypedDict, total=False):
    query: str
    web: list[SearchResultItem]
    news: list[SearchResultItem]
    images: list[SearchResultItem]
    result_count: int


class MapLinkItem(TypedDict, total=False):
    url: str
    title: Optional[str]
    description: Optional[str]


class MapWebsiteOutput(TypedDict, total=False):
    url: str
    links: list[MapLinkItem]
    link_count: int


class CrawlDocumentItem(TypedDict, total=False):
    url: str
    title: Optional[str]
    markdown: Optional[str]


class CrawlWebsiteOutput(TypedDict, total=False):
    job_id: str
    status: str
    completed: int
    total: int
    credits_used: int
    data: list[CrawlDocumentItem]
    next_action_hint: Optional[str]


class CrawlStatusOutput(TypedDict, total=False):
    job_id: str
    status: str
    completed: int
    total: int
    credits_used: int
    next_action_hint: Optional[str]


class CrawlDataOutput(TypedDict, total=False):
    job_id: str
    status: str
    completed: int
    total: int
    data: list[CrawlDocumentItem]
    next_action_hint: Optional[str]


class CancelCrawlOutput(TypedDict):
    job_id: str
    cancelled: bool


class ExtractDataOutput(TypedDict, total=False):
    job_id: str
    status: str
    # JSON-serialized extract payload (Arcade rejects typing.Any on the wire).
    data_json: Optional[str]
    error: Optional[str]
    credits_used: Optional[int]
    model: Optional[str]
    next_action_hint: Optional[str]


class ExtractStatusOutput(TypedDict, total=False):
    job_id: str
    status: str
    data_json: Optional[str]
    error: Optional[str]
    credits_used: Optional[int]
    next_action_hint: Optional[str]


class DeveloperSearchHit(TypedDict, total=False):
    title: Optional[str]
    url: Optional[str]
    type: Optional[str]
    repo: Optional[str]
    score: Optional[float]
    passages: list[str]


class DeveloperSearchOutput(TypedDict, total=False):
    query: str
    results: list[DeveloperSearchHit]
    result_count: int


class ResearchPaperItem(TypedDict, total=False):
    paper_id: str
    title: Optional[str]
    abstract: Optional[str]
    authors: list[str]
    year: Optional[int]
    url: Optional[str]
    source: Optional[str]
    citation_count: Optional[int]
    categories: Optional[list[str]]


class SearchResearchPapersOutput(TypedDict, total=False):
    query: str
    papers: list[ResearchPaperItem]
    result_count: int


class GithubIssueItem(TypedDict, total=False):
    title: Optional[str]
    url: Optional[str]
    repo: Optional[str]
    state: Optional[str]
    number: Optional[int]
    body_excerpt: Optional[str]


class SearchGithubIssuesOutput(TypedDict, total=False):
    query: str
    issues: list[GithubIssueItem]
    result_count: int
