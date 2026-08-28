"""Research tools: developer docs, papers, GitHub issues."""

from typing import Annotated, Any, Optional

from arcade_mcp_server import Context, tool
from arcade_tdk.errors import RetryableToolError

from firecrawl_arcade.client import get_firecrawl_client
from firecrawl_arcade.constants import (
    DEFAULT_DEVELOPER_K,
    DEFAULT_PASSAGES,
    DEFAULT_RESEARCH_K,
    MAX_DEVELOPER_K,
    MAX_PASSAGES,
    MAX_RESEARCH_K,
    MIN_LIMIT,
    clamp,
)
from firecrawl_arcade.errors import FIRECRAWL_ADAPTERS
from firecrawl_arcade.metadata import READ_METADATA
from firecrawl_arcade.models.outputs import (
    DeveloperSearchOutput,
    SearchGithubIssuesOutput,
    SearchResearchPapersOutput,
)
from firecrawl_arcade.shaping import (
    shape_developer_hit,
    shape_github_issue,
    shape_paper,
)

_SECRET = ["FIRECRAWL_API_KEY"]


def _as_list(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


@tool(
    name="SearchDeveloperDocs",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def search_developer_docs(
    context: Context,
    query: Annotated[str, "Developer search query (docs, READMEs, issues, PRs)"],
    k: Annotated[
        int,
        f"Max results (min {MIN_LIMIT}, max {MAX_DEVELOPER_K})",
    ] = DEFAULT_DEVELOPER_K,
    passages: Annotated[
        int,
        f"Evidence passages per result (min {MIN_LIMIT}, max {MAX_PASSAGES})",
    ] = DEFAULT_PASSAGES,
    repos: Annotated[
        Optional[list[str]],
        "Optional owner/repo filters, e.g. ['firecrawl/firecrawl'].",
    ] = None,
    language: Annotated[
        Optional[str],
        "Optional programming language filter (e.g. 'python', 'typescript').",
    ] = None,
) -> Annotated[DeveloperSearchOutput, "Developer index hits with evidence passages"]:
    """Search Firecrawl's developer index for docs, READMEs, issues, and PRs.

    Prefer this over Search when the need is code or API documentation evidence.
    Prefer SearchGithubIssues for GitHub-issue-only queries.
    """
    if not query.strip():
        raise RetryableToolError(
            message="query must be a non-empty developer search string.",
            developer_message="empty query",
            additional_prompt_content="Example: 'firecrawl scrape python sdk timeout'.",
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    k = clamp(k, MIN_LIMIT, MAX_DEVELOPER_K)
    passages = clamp(passages, MIN_LIMIT, MAX_PASSAGES)

    kwargs: dict[str, Any] = {"k": k, "passages": passages}
    if repos:
        kwargs["repos"] = repos
    if language:
        kwargs["language"] = language

    response = await client.developer_search(query, **kwargs)
    raw_results = getattr(response, "results", None) or []
    hits = [shape_developer_hit(item) for item in raw_results]
    return DeveloperSearchOutput(query=query, results=hits, result_count=len(hits))


@tool(
    name="SearchResearchPapers",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def search_research_papers(
    context: Context,
    query: Annotated[str, "Scientific literature search query"],
    k: Annotated[
        int,
        f"Max papers to return (min {MIN_LIMIT}, max {MAX_RESEARCH_K})",
    ] = DEFAULT_RESEARCH_K,
    authors: Annotated[
        Optional[list[str]],
        "Optional author name filters.",
    ] = None,
    categories: Annotated[
        Optional[list[str]],
        "Optional subject categories (e.g. arXiv categories).",
    ] = None,
    include_inspect: Annotated[
        bool,
        "If true (default), fold inspect_paper metadata into the top results.",
    ] = True,
) -> Annotated[SearchResearchPapersOutput, "Ranked research papers with abstracts"]:
    """Search Firecrawl's research paper index (~43M abstracts) and return papers.

    This queries the paper corpus (PubMed, bioRxiv, medRxiv, arXiv), not ordinary
    web pages. For academic *websites* via web search, use Search with category research.
    """
    if not query.strip():
        raise RetryableToolError(
            message="query must be a non-empty literature search string.",
            developer_message="empty query",
            additional_prompt_content="Example: 'CRISPR base editing off-target effects 2024'.",
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    k = clamp(k, MIN_LIMIT, MAX_RESEARCH_K)
    kwargs: dict[str, Any] = {"k": k}
    if authors:
        kwargs["authors"] = authors
    if categories:
        kwargs["categories"] = categories

    raw = await client.search_papers(query, **kwargs)
    papers_raw = _as_list(raw, "papers", "results", "data")
    papers = []
    for item in papers_raw[:k]:
        inspect_meta = None
        if include_inspect:
            paper_id = None
            if isinstance(item, dict):
                paper_id = item.get("paperId") or item.get("paper_id") or item.get("primaryId")
            if paper_id:
                try:
                    inspect_meta = await client.inspect_paper(str(paper_id))
                    if isinstance(inspect_meta, dict):
                        inspect_meta = (
                            inspect_meta.get("paper")
                            or inspect_meta.get("data")
                            or inspect_meta
                        )
                except Exception:
                    inspect_meta = None
        papers.append(shape_paper(item, inspect_meta if isinstance(inspect_meta, dict) else None))

    return SearchResearchPapersOutput(query=query, papers=papers, result_count=len(papers))


@tool(
    name="SearchGithubIssues",
    requires_secrets=_SECRET,
    adapters=FIRECRAWL_ADAPTERS,
    metadata=READ_METADATA,
)
async def search_github_issues(
    context: Context,
    query: Annotated[str, "GitHub issues search query"],
    k: Annotated[
        int,
        f"Max issues to return (min {MIN_LIMIT}, max {MAX_RESEARCH_K})",
    ] = DEFAULT_RESEARCH_K,
) -> Annotated[SearchGithubIssuesOutput, "Matching GitHub issues"]:
    """Search GitHub issues via Firecrawl's research/GitHub index.

    Prefer SearchDeveloperDocs for broader docs/README/PR hits.
    """
    if not query.strip():
        raise RetryableToolError(
            message="query must be a non-empty GitHub issues search string.",
            developer_message="empty query",
            additional_prompt_content="Example: 'rate limit 429 firecrawl scrape'.",
            retry_after_ms=100,
        )

    client = get_firecrawl_client(context)
    k = clamp(k, MIN_LIMIT, MAX_RESEARCH_K)
    raw = await client.search_github(query, k=k)
    issues_raw = _as_list(raw, "issues", "results", "data")
    issues = [shape_github_issue(item) for item in issues_raw]
    return SearchGithubIssuesOutput(query=query, issues=issues, result_count=len(issues))
