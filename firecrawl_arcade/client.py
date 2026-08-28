"""Firecrawl client factory with secret resolution and Arcade origin attribution."""

from __future__ import annotations

import asyncio
import inspect
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from arcade_mcp_server import Context
from firecrawl import AsyncFirecrawl

from firecrawl_arcade.constants import ARCADE_ORIGIN

_ORIGIN_RE = re.compile(r"([?&])origin=[^&]*")


def _rewrite_origin_in_url(endpoint: str, origin: str) -> str:
    """Replace or append origin= in a path+query endpoint string."""
    if "origin=" in endpoint:
        return _ORIGIN_RE.sub(rf"\1origin={origin}", endpoint, count=1)

    parsed = urlparse(endpoint)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["origin"] = origin
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _supports_origin_kwarg() -> bool:
    try:
        return "origin" in inspect.signature(AsyncFirecrawl.__init__).parameters
    except (TypeError, ValueError):
        return False


def _patch_origin(client: AsyncFirecrawl, origin: str = ARCADE_ORIGIN) -> AsyncFirecrawl:
    """Fallback: override baked-in origin on older firecrawl-py builds."""
    http = client._v2_client.async_http_client

    async def post_with_origin(
        endpoint: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
    ):
        payload = dict(data)
        payload["origin"] = origin
        return await _request_loop(
            http,
            "POST",
            endpoint,
            json_body=payload,
            headers=headers,
            timeout=timeout,
            retries=retries,
            backoff_factor=backoff_factor,
        )

    async def get_with_origin(
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
    ):
        rewritten = _rewrite_origin_in_url(endpoint, origin)
        return await _request_loop(
            http,
            "GET",
            rewritten,
            headers=headers,
            timeout=timeout,
            retries=retries,
            backoff_factor=backoff_factor,
        )

    http.post = post_with_origin  # type: ignore[method-assign]
    http.get = get_with_origin  # type: ignore[method-assign]
    return client


async def _request_loop(
    http: Any,
    method: str,
    endpoint: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None,
    retries: int | None,
    backoff_factor: float | None,
) -> httpx.Response:
    if timeout is None:
        timeout = http.timeout
    if retries is None:
        retries = http.max_retries
    if backoff_factor is None:
        backoff_factor = http.backoff_factor

    last_exception: Exception | None = None
    num_attempts = max(1, retries)
    merged_headers = {**http._headers(), **(headers or {})}

    for attempt in range(num_attempts):
        try:
            if method == "POST":
                response = await http._client.post(
                    endpoint, json=json_body, headers=merged_headers, timeout=timeout
                )
            else:
                response = await http._client.get(
                    endpoint, headers=merged_headers, timeout=timeout
                )
            if response.status_code == 502 and attempt < num_attempts - 1:
                await asyncio.sleep(backoff_factor * (2**attempt))
                continue
            return response
        except httpx.HTTPError as exc:
            last_exception = exc
            if attempt == num_attempts - 1:
                raise
            await asyncio.sleep(backoff_factor * (2**attempt))

    raise last_exception or RuntimeError(f"Unexpected error in Firecrawl {method}")


def get_firecrawl_client(context: Context) -> AsyncFirecrawl:
    """Build an AsyncFirecrawl client from the Arcade-injected API key secret."""
    api_key = context.get_secret("FIRECRAWL_API_KEY")
    kwargs: dict[str, Any] = {"api_key": api_key}
    try:
        api_url = context.get_secret("FIRECRAWL_API_URL")
        if api_url:
            kwargs["api_url"] = api_url
    except Exception:
        pass

    if _supports_origin_kwarg():
        kwargs["origin"] = ARCADE_ORIGIN
        return AsyncFirecrawl(**kwargs)

    return _patch_origin(AsyncFirecrawl(**kwargs))
