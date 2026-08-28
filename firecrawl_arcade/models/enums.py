"""Constrained input enums for Firecrawl Arcade tools."""

from enum import Enum


class OutputFormat(str, Enum):
    """Scrape output formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    RAW_HTML = "rawHtml"
    LINKS = "links"
    SCREENSHOT = "screenshot"
    SUMMARY = "summary"
    JSON = "json"


class ProxyMode(str, Enum):
    """Proxy selection for scrape/crawl."""

    BASIC = "basic"
    STEALTH = "stealth"
    ENHANCED = "enhanced"
    AUTO = "auto"


class SitemapMode(str, Enum):
    """How crawl/map should treat the site sitemap."""

    INCLUDE = "include"
    SKIP = "skip"
    ONLY = "only"


class SearchCategory(str, Enum):
    """Web search category filters (not the research paper index)."""

    GITHUB = "github"
    RESEARCH = "research"
    PDF = "pdf"
    DEVELOPER = "developer"


class SearchSource(str, Enum):
    """Search result source types."""

    WEB = "web"
    NEWS = "news"
    IMAGES = "images"


class AgentModel(str, Enum):
    """Firecrawl agent (ExtractData) model choices."""

    SPARK_1_MINI = "spark-1-mini"
    SPARK_1_PRO = "spark-1-pro"
    SPARK_2 = "spark-2"


class AgentEffort(str, Enum):
    """Reasoning effort for ExtractData."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
