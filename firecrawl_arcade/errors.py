"""Error adapter mapping firecrawl-py exceptions into Arcade runtime errors."""

from __future__ import annotations

from arcade_tdk.errors import (
    ToolExecutionError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)


class FirecrawlErrorAdapter:
    """Translate firecrawl-py SDK exceptions into Arcade ToolRuntimeError types.

    Without this adapter, Firecrawl SDK exceptions fall through to FatalToolError
    and lose retryability / rate-limit semantics.
    """

    slug = "_firecrawl_py"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        try:
            from firecrawl.v2.utils.error_handler import (
                BadRequestError,
                FirecrawlError,
                InternalServerError,
                PaymentRequiredError,
                RateLimitError,
                RequestTimeoutError,
                UnauthorizedError,
                WebsiteNotSupportedError,
            )
        except ImportError:
            return None

        if isinstance(exc, RateLimitError):
            return UpstreamRateLimitError(
                message="Firecrawl rate limit exceeded. Retry after a short delay.",
                developer_message=str(exc),
                retry_after_ms=2000,
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, BadRequestError):
            return UpstreamError(
                message=f"Invalid Firecrawl request: {exc}",
                status_code=getattr(exc, "status_code", 400) or 400,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, UnauthorizedError):
            return UpstreamError(
                message="Firecrawl API key is missing or invalid.",
                status_code=401,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, PaymentRequiredError):
            return UpstreamError(
                message="Firecrawl account requires payment or has insufficient credits.",
                status_code=402,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, WebsiteNotSupportedError):
            return UpstreamError(
                message="Firecrawl cannot access this website.",
                status_code=403,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, RequestTimeoutError):
            return UpstreamError(
                message="Firecrawl request timed out. Retry or narrow the request scope.",
                status_code=408,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, InternalServerError):
            return UpstreamError(
                message="Firecrawl encountered an internal server error.",
                status_code=500,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, FirecrawlError):
            status = getattr(exc, "status_code", 500) or 500
            return UpstreamError(
                message=f"Firecrawl API error: {exc}",
                status_code=status,
                developer_message=str(exc),
                extra={"service": self.slug, "error_type": type(exc).__name__},
            )

        if isinstance(exc, TimeoutError):
            # Bounded-wait overruns are handled in tools; leftover TimeoutErrors
            # become execution errors with a clear message.
            return ToolExecutionError(
                message="Operation timed out before Firecrawl finished.",
                developer_message=str(exc),
            )

        return None


FIRECRAWL_ADAPTERS = [FirecrawlErrorAdapter()]
