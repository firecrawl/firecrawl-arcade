"""Shared limits, defaults, and attribution for Firecrawl Arcade tools."""

# Origin string stamped into Firecrawl API request payloads for usage attribution.
ARCADE_ORIGIN = "arcade-mcp"

# Bounded-wait budgets for long-running jobs (seconds).
CRAWL_WAIT_BUDGET_SECONDS = 60
EXTRACT_WAIT_BUDGET_SECONDS = 90
DEFAULT_POLL_INTERVAL_SECONDS = 2

# Numeric clamps.
MIN_LIMIT = 1
MAX_SEARCH_LIMIT = 20
DEFAULT_SEARCH_LIMIT = 5
MAX_MAP_LIMIT = 5000
DEFAULT_MAP_LIMIT = 100
MAX_CRAWL_LIMIT = 100
DEFAULT_CRAWL_LIMIT = 10
MAX_RESEARCH_K = 25
DEFAULT_RESEARCH_K = 10
MAX_DEVELOPER_K = 25
DEFAULT_DEVELOPER_K = 8
MAX_PASSAGES = 5
DEFAULT_PASSAGES = 2

# Truncation for token-efficient responses.
MAX_MARKDOWN_CHARS = 12_000
MAX_DESCRIPTION_CHARS = 500


def clamp(value: int, low: int, high: int) -> int:
    """Clamp an integer into [low, high]."""
    return min(max(value, low), high)


def truncate(text: str | None, max_chars: int) -> str | None:
    """Truncate text for token-efficient tool outputs."""
    if text is None:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"
