"""Shared ToolMetadata presets for Firecrawl tools."""

from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

WEB_SCRAPING = Classification(service_domains=[ServiceDomain.WEB_SCRAPING])

READ_METADATA = ToolMetadata(
    classification=WEB_SCRAPING,
    behavior=Behavior(
        operations=[Operation.READ],
        read_only=True,
        destructive=False,
        idempotent=False,
        open_world=True,
    ),
)

# CancelCrawl: deletes/cancels an in-flight job. Idempotent cancel.
CANCEL_METADATA = ToolMetadata(
    classification=WEB_SCRAPING,
    behavior=Behavior(
        operations=[Operation.DELETE],
        read_only=False,
        destructive=True,
        idempotent=True,
        open_world=True,
    ),
)
