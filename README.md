# Firecrawl Arcade Toolkit

An [Arcade](https://arcade.dev) MCP server that exposes [Firecrawl](https://www.firecrawl.dev) web scraping, search, crawling, and structured extraction as tools for any MCP-compatible client, on Firecrawl API v2.

Built on [`arcade-mcp-server`](https://pypi.org/project/arcade-mcp-server/). It ships twelve intent-shaped tools with an eval suite that separates the commonly confused scrape / search / map / crawl / extract decision. The six tool names from the earlier `arcade-firecrawl` toolkit are preserved so existing callers keep working.

## Tools

| Tool | Description |
| --- | --- |
| `Firecrawl.ScrapeUrl` | Scrape one known URL and return its content. |
| `Firecrawl.Search` | Search the web, with optional inline scrape of the results. |
| `Firecrawl.MapWebsite` | Discover the URLs on a site. |
| `Firecrawl.CrawlWebsite` | Crawl a site with a bounded wait. Returns a job id if the wait is exceeded. |
| `Firecrawl.GetCrawlStatus` | Poll a crawl job. |
| `Firecrawl.GetCrawlData` | Fetch the pages a crawl job collected. |
| `Firecrawl.CancelCrawl` | Cancel a crawl job. The only non-read-only tool. |
| `Firecrawl.ExtractData` | Autonomous structured extraction with a bounded wait. |
| `Firecrawl.GetExtractStatus` | Poll an extraction job. |
| `Firecrawl.SearchDeveloperDocs` | Search the developer documentation index. |
| `Firecrawl.SearchResearchPapers` | Search the research paper index, with inspect metadata folded in. |
| `Firecrawl.SearchGithubIssues` | Search GitHub issues. |

All tools require a `FIRECRAWL_API_KEY`, injected as a server-side secret. It is never exposed to the LLM or the MCP client.

### Preserved tool names

`ScrapeUrl`, `MapWebsite`, `CrawlWebsite`, `GetCrawlStatus`, `GetCrawlData`, and `CancelCrawl` keep their names from the earlier `arcade-firecrawl` toolkit, so agents and gateways that already call them keep working. Under the hood they call Firecrawl API v2 via `firecrawl-py>=4.40`.

### Not included

- `interact` / `stop_interact`: stateful browser sessions.
- `ReadResearchPaper`: would fold `read_paper` and `find_related_papers` into one tool.
- Monitor create, read, update, and delete.
- `parse`: takes a local file path, which does not fit hosted execution. `ScrapeUrl` handles PDF URLs.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- A [Firecrawl API key](https://www.firecrawl.dev/app/api-keys)

## Quick start

```bash
uv tool install arcade-mcp
uv sync --extra dev
cp .env.example .env   # set FIRECRAWL_API_KEY
make server            # stdio transport
```

Use stdio locally. The local HTTP transport cannot inject secrets. To use the server from Cursor:

```bash
arcade configure cursor
```

## Configuration

| Environment variable | Required | Description |
| --- | --- | --- |
| `FIRECRAWL_API_KEY` | Yes | Firecrawl API key. |
| `FIRECRAWL_API_URL` | No | Override the API base URL. Defaults to `https://api.firecrawl.dev`. |

## Tool metadata

Every tool declares:

```python
ToolMetadata(
    classification=Classification(service_domains=[ServiceDomain.WEB_SCRAPING]),
    behavior=Behavior(
        operations=[Operation.READ],  # DELETE for CancelCrawl
        read_only=True,               # False for CancelCrawl
        destructive=False,            # True for CancelCrawl
        idempotent=False,             # True for CancelCrawl
        open_world=True,              # required when a ServiceDomain is set
    ),
)
```

## Error handling

`FirecrawlErrorAdapter` maps `firecrawl-py` exceptions (`RateLimitError`, `BadRequestError`, and others) to Arcade `UpstreamRateLimitError`, `UpstreamError`, or `ToolExecutionError`. Invalid caller input raises `RetryableToolError` with `additional_prompt_content` so the LLM can recover.

## Attribution

Requests carry `origin=arcade-mcp` so usage through this server is attributable in Firecrawl metrics.

1. Preferred: pass `origin=` to `AsyncFirecrawl` / `Firecrawl` ([firecrawl-py PR #4440](https://github.com/firecrawl/firecrawl/pull/4440)).
2. Fallback in this server: patch the async HTTP client POST body and the research GET query when the installed `firecrawl-py` build lacks the constructor argument.

## Development

```bash
make install   # dependencies, including dev extras
make test      # unit tests, no API key required
make lint      # ruff
make evals     # eval suite, needs OPENAI_API_KEY
make smoke     # live smoke test against API v2, needs FIRECRAWL_API_KEY
```

### Evals

`evals/eval_firecrawl.py` checks tool selection for five commonly confused intents:

| User intent | Expected tool |
| --- | --- |
| Get me this known page | `Firecrawl_ScrapeUrl` |
| Find articles about X | `Firecrawl_Search` |
| What pages does this site have | `Firecrawl_MapWebsite` |
| Read this whole docs site | `Firecrawl_CrawlWebsite` |
| Pull every product name and price | `Firecrawl_ExtractData` |

Rubric: `fail_threshold=0.8`, `warn_threshold=0.9`. To pick the model:

```bash
export OPENAI_API_KEY=...
uv run arcade evals . -m gpt-4o-mini
```

### Live smoke test

`scripts/smoke_live.py` exercises every tool against the live API. A 409 from `CancelCrawl` on an already-completed job is treated as settled.

## Deploy to Arcade Cloud

```bash
arcade login
arcade secret set FIRECRAWL_API_KEY=fc-...
arcade deploy -e firecrawl_arcade/server.py
```

`app.run()` is guarded by `if __name__ == "__main__":`, as `arcade deploy` requires.

## Project structure

```
firecrawl_arcade/
  server.py          MCPApp(name="Firecrawl")
  client.py          AsyncFirecrawl + origin patch + secret resolution
  errors.py          FirecrawlErrorAdapter
  constants.py       budgets, clamps, attribution
  metadata.py        ToolMetadata presets
  shaping.py         response shapers
  models/enums.py
  models/outputs.py
  tools/web.py
  tools/research.py
evals/eval_firecrawl.py
tests/
scripts/smoke_live.py
```

## License

MIT. See [LICENSE](LICENSE).
