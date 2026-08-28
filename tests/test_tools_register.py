"""Smoke-test helpers for stdio tool registration (no live API required)."""

from firecrawl_arcade.server import app


def test_app_name() -> None:
    assert app.name == "Firecrawl"


def test_twelve_tools_registered() -> None:
    names = sorted(t.name for t in app._catalog)
    expected = sorted(
        [
            "ScrapeUrl",
            "Search",
            "MapWebsite",
            "CrawlWebsite",
            "GetCrawlStatus",
            "GetCrawlData",
            "CancelCrawl",
            "ExtractData",
            "GetExtractStatus",
            "SearchDeveloperDocs",
            "SearchResearchPapers",
            "SearchGithubIssues",
        ]
    )
    assert names == expected
