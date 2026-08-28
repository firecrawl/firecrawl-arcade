.PHONY: install test lint server evals smoke

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest -q

lint:
	uv run ruff check firecrawl_arcade tests evals

server:
	uv run python -m firecrawl_arcade.server stdio

evals:
	uv run arcade evals .

smoke:
	uv run python scripts/smoke_live.py
