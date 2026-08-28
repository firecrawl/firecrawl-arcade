"""Arcade MCP entrypoint for the Firecrawl toolkit."""

from __future__ import annotations

import sys
from typing import cast

from arcade_mcp_server import MCPApp
from arcade_mcp_server.mcp_app import TransportType

import firecrawl_arcade

app = MCPApp(
    name="Firecrawl",
    version="1.0.0",
    instructions=(
        "Firecrawl tools for web scraping, search, site mapping, crawling, "
        "structured extraction, developer-docs search, and research papers. "
        "Prefer Search when the URL is unknown, ScrapeUrl for one known page, "
        "MapWebsite to list URLs, CrawlWebsite for multi-page content, and "
        "ExtractData for structured fields across unknown pages."
    ),
)

app.add_tools_from_module(firecrawl_arcade)


def main() -> None:
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    app.run(transport=cast(TransportType, transport), host=host, port=port)


if __name__ == "__main__":
    main()
