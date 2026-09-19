# Firecrawl Arcade Toolkit

Arcade MCP server that replaces Arcade's bundled `arcade-firecrawl` (API v1, 6 tools) with an **Optimized** Firecrawl toolkit on **API v2**.

Hand this repo to Arcade for inclusion in the official toolkit catalog so Firecrawl stays on the Optimized tier and ships as a default install.

## Why this shape

Arcade grades toolkits as [Optimized vs Unoptimized](https://docs.arcade.dev/en/build/create-tools/improve/types-of-tools). A 1:1 wrapper of every Firecrawl endpoint would be Unoptimized and would downgrade the existing Optimized Firecrawl listing. This server instead ships **12 intent-shaped tools** with eval coverage that separates the confusable scrape / search / map / crawl / extract decision.

## Tools (12)

| Tool | Purpose | Notes |
| --- | --- | --- |
| `Firecrawl.ScrapeUrl` | Scrape one known URL | Preserved name from v1 toolkit |
| `Firecrawl.Search` | Web search + optional inline scrape | Task bundle (highest-value new tool) |
| `Firecrawl.MapWebsite` | Discover URLs on a site | Preserved name |
| `Firecrawl.CrawlWebsite` | Multi-page crawl with bounded wait | Preserved name; returns job id on overrun |
| `Firecrawl.GetCrawlStatus` | Poll crawl status | Preserved name |
| `Firecrawl.GetCrawlData` | Fetch crawl page data | Preserved name |
| `Firecrawl.CancelCrawl` | Cancel a crawl | Preserved name; only non-read-only tool |
| `Firecrawl.ExtractData` | Autonomous structured extraction (`/agent`) | Bounded wait |
| `Firecrawl.GetExtractStatus` | Poll extract/agent job | |
| `Firecrawl.SearchDeveloperDocs` | Developer index search | |
| `Firecrawl.SearchResearchPapers` | Paper index + folded inspect metadata | |
| `Firecrawl.SearchGithubIssues` | GitHub issues search | |

### Migration from Arcade's current Firecrawl toolkit

The six existing tool names are preserved verbatim so agents and gateways that already call them keep working after Arcade swaps the implementation:

`ScrapeUrl`, `MapWebsite`, `CrawlWebsite`, `GetCrawlStatus`, `GetCrawlData`, `CancelCrawl`

Under the hood they now call Firecrawl **API v2** via `firecrawl-py>=4.40`.

### Deferred (phase 2)

- `interact` / `stop_interact` (stateful browser sessions)
- `ReadResearchPaper` (fold `read_paper` + `find_related_papers`)
- Monitor CRUD (8 endpoints; discuss with Arcade whether persistent monitors belong in an agent toolkit)
- `parse` dropped: local-file-path API, incompatible with hosted execution; covered by `ScrapeUrl` for PDF URLs

## Secrets

| Secret | Required | Purpose |
| --- | --- | --- |
| `FIRECRAWL_API_KEY` | Yes | Bearer auth for `https://api.firecrawl.dev` |
| `FIRECRAWL_API_URL` | No | Override API base URL |

Copy `.env.example` to `.env` for local stdio testing.

## ToolMetadata

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

`FirecrawlErrorAdapter` maps `firecrawl-py` exceptions (`RateLimitError`, `BadRequestError`, …) to Arcade `UpstreamRateLimitError` / `UpstreamError` / `ToolExecutionError`. Invalid caller input raises `RetryableToolError` with `additional_prompt_content` so the LLM can recover.

## Local development

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install arcade-mcp
uv sync --extra dev
cp .env.example .env   # set FIRECRAWL_API_KEY

# Load tools (stdio). Local HTTP cannot use secrets.
uv run python -m firecrawl_arcade.server stdio

# Unit tests (no API key required)
uv run pytest

# Eval suite (needs OPENAI_API_KEY)
uv run arcade evals .
```

Configure Cursor over **stdio** (not http) so secrets inject:

```bash
arcade configure cursor
```

## Evals

`evals/eval_firecrawl.py` gates tool selection for the five confusable intents:

| User intent | Expected tool |
| --- | --- |
| Get me this known page | `Firecrawl_ScrapeUrl` |
| Find articles about X | `Firecrawl_Search` |
| What pages does this site have | `Firecrawl_MapWebsite` |
| Read this whole docs site | `Firecrawl_CrawlWebsite` |
| Pull every product name and price | `Firecrawl_ExtractData` |

Rubric: `fail_threshold=0.8`, `warn_threshold=0.9`.

## Attribution

Requests stamp `origin=arcade-mcp` so Arcade usage is attributable in Firecrawl metrics.

1. Preferred: pass `origin=` into `AsyncFirecrawl` / `Firecrawl` ([python-sdk PR #4440](https://github.com/firecrawl/firecrawl/pull/4440)).
2. Fallback in this server: patch the async HTTP client POST body and research GET query when the installed `firecrawl-py` build lacks the constructor kwarg.

## Eval results

Suite: `evals/eval_firecrawl.py` (5 cases, rubric 0.8 / 0.9).

Run before deploy:

```bash
export OPENAI_API_KEY=...
uv run arcade evals . -m gpt-4o-mini
```

Live tool smoke (`scripts/smoke_live.py`) against API v2: ScrapeUrl, Search, MapWebsite, CrawlWebsite, GetCrawlStatus, GetCrawlData, CancelCrawl (409 on already-completed treated as settled), ExtractData, GetExtractStatus, SearchDeveloperDocs, SearchResearchPapers, SearchGithubIssues.

## Deploy (Arcade Cloud)

```bash
arcade login
arcade secret set FIRECRAWL_API_KEY=fc-...
arcade deploy -e firecrawl_arcade/server.py
```

`app.run()` is guarded by `if __name__ == "__main__":` as required by `arcade deploy`.

## Layout

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
```

## Verification checklist

1. Tool inventory: the six preserved names (`ScrapeUrl`, `MapWebsite`, `CrawlWebsite`, `GetCrawlStatus`, `GetCrawlData`, `CancelCrawl`) resolve to the tools listed above
2. Secrets: `FIRECRAWL_API_KEY` is set (`.env` over stdio locally, Arcade Cloud secrets when deployed)
3. Evals: `uv run arcade evals .` passes the five confusable-intent cases
4. Deploy: `arcade deploy -e firecrawl_arcade/server.py` behind an MCP Gateway

## License

MIT. See [LICENSE](LICENSE).
