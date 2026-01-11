"""HTTPS enforcement middleware."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _parse_forwarded_proto(header_value: str | None) -> str | None:
    if not header_value:
        return None
    for part in header_value.split(","):
        for token in part.split(";"):
            key, _, value = token.strip().partition("=")
            if key.lower() == "proto" and value:
                return value.strip().strip('"').lower()
    return None


def is_https_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        proto = forwarded_proto.split(",")[0].strip().lower()
        if proto:
            return proto == "https"

    proto = _parse_forwarded_proto(request.headers.get("forwarded"))
    if proto:
        return proto == "https"

    return request.url.scheme == "https"


class RequireHTTPSMiddleware(BaseHTTPMiddleware):
    """Reject HTTP requests when HTTPS is required."""

    def __init__(self, app, require_https: bool, allow_http_dev: bool, environment: str) -> None:
        super().__init__(app)
        self.require_https = require_https
        self.allow_http_dev = allow_http_dev
        self.environment = (environment or "development").lower()

    def _is_allowed(self, request: Request) -> bool:
        if not self.require_https:
            return True
        if self.allow_http_dev and self.environment in {"development", "testing"}:
            return True
        return is_https_request(request)

    async def dispatch(self, request: Request, call_next):
        if self._is_allowed(request):
            return await call_next(request)

        host = request.headers.get("host")
        upgrade_url = None
        if host:
            upgrade_url = f"https://{host}{request.url.path}"
            if request.url.query:
                upgrade_url = f"{upgrade_url}?{request.url.query}"

        return JSONResponse(
            status_code=426,
            content={"detail": "HTTPS is required", "upgrade_url": upgrade_url},
        )
