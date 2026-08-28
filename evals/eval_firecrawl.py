"""Eval suite: tool selection for confusable Firecrawl intents."""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
    tool_eval,
)
from arcade_core import ToolCatalog

import firecrawl_arcade
from firecrawl_arcade.tools.web import (
    crawl_website,
    extract_data,
    map_website,
    scrape_url,
    search,
)

rubric = EvalRubric(fail_threshold=0.8, warn_threshold=0.9)

catalog = ToolCatalog()
catalog.add_module(firecrawl_arcade)


@tool_eval()
def firecrawl_eval_suite() -> EvalSuite:
    """Gate the scrape vs search vs map vs crawl vs extract decision."""
    suite = EvalSuite(
        name="Firecrawl Optimized Tools",
        system_message=(
            "You are an AI assistant with Firecrawl tools for web scraping, "
            "search, mapping, crawling, and structured extraction. "
            "Pick the single best tool for the user's intent."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Scrape a known pricing page",
        user_message="Get me the content of https://www.firecrawl.dev/pricing as markdown.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=scrape_url,
                args={"url": "https://www.firecrawl.dev/pricing"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=1.0),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Search for articles when URL is unknown",
        user_message="Find recent articles about LLM web scraping benchmarks.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search,
                args={"query": "LLM web scraping benchmarks"},
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Map a docs site for URLs",
        user_message="What pages does https://docs.firecrawl.dev have? Just list the URLs.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=map_website,
                args={"url": "https://docs.firecrawl.dev"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=1.0),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Crawl a whole docs site for content",
        user_message=(
            "Read the whole https://docs.firecrawl.dev site and return the page content. "
            "Limit to about 10 pages."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=crawl_website,
                args={"url": "https://docs.firecrawl.dev", "limit": 10},
            )
        ],
        critics=[
            BinaryCritic(critic_field="url", weight=0.7),
            NumericCritic(
                critic_field="limit",
                weight=0.3,
                value_range=(5.0, 15.0),
            ),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Extract structured product data",
        user_message=(
            "Pull every product name and price from https://example.com/store "
            "into a structured list."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=extract_data,
                args={
                    "prompt": "Extract every product name and price",
                    "urls": ["https://example.com/store"],
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="prompt", weight=0.6),
            BinaryCritic(critic_field="urls", weight=0.4),
        ],
        rubric=rubric,
    )

    return suite
