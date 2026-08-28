"""Unit tests for Firecrawl Arcade helpers (no live API)."""

from firecrawl_arcade.constants import clamp, truncate
from firecrawl_arcade.client import _rewrite_origin_in_url
from firecrawl_arcade.errors import FirecrawlErrorAdapter
from firecrawl_arcade.shaping import shape_map_link, shape_paper, shape_search_item


def test_clamp() -> None:
    assert clamp(0, 1, 10) == 1
    assert clamp(5, 1, 10) == 5
    assert clamp(99, 1, 10) == 10


def test_truncate() -> None:
    assert truncate(None, 10) is None
    assert truncate("short", 10) == "short"
    assert truncate("abcdefghijklmnop", 8) == "abcdefg…"


def test_rewrite_origin_in_url() -> None:
    assert (
        _rewrite_origin_in_url("/v2/search/research/papers?query=x&origin=python-sdk@1", "arcade-mcp")
        == "/v2/search/research/papers?query=x&origin=arcade-mcp"
    )
    rewritten = _rewrite_origin_in_url("/v2/search/research/papers?query=x", "arcade-mcp")
    assert "origin=arcade-mcp" in rewritten


def test_shape_map_link_string() -> None:
    assert shape_map_link("https://example.com")["url"] == "https://example.com"


def test_shape_paper_dict() -> None:
    paper = shape_paper(
        {
            "paperId": "pmid:123",
            "title": "Example",
            "abstract": "Hello",
            "authors": [{"name": "Ada"}],
            "year": 2024,
        }
    )
    assert paper["paper_id"] == "pmid:123"
    assert paper["authors"] == ["Ada"]


class _Item:
    def __init__(self) -> None:
        self.url = "https://example.com"
        self.title = "Title"
        self.description = "Desc"
        self.position = 1


def test_shape_search_item() -> None:
    item = shape_search_item(_Item())
    assert item["url"] == "https://example.com"
    assert item["title"] == "Title"


def test_error_adapter_unknown() -> None:
    adapter = FirecrawlErrorAdapter()
    assert adapter.from_exception(ValueError("nope")) is None
