"""Middleware to support /api prefixed routes (reverse proxy/tunnel)."""

from starlette.types import ASGIApp, Receive, Scope, Send


class ApiPrefixMiddleware:
    """Strip a fixed prefix from incoming paths so /api/* maps to app routes."""

    def __init__(self, app: ASGIApp, prefix: str = "/api") -> None:
        self.app = app
        self.prefix = prefix.rstrip("/") or "/api"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") in ("http", "websocket"):
            path = scope.get("path") or ""
            if path == self.prefix or path.startswith(f"{self.prefix}/"):
                new_path = path[len(self.prefix) :] or "/"
                updated_scope = dict(scope)
                updated_scope["path"] = new_path
                raw_path = scope.get("raw_path")
                if isinstance(raw_path, (bytes, bytearray)):
                    updated_scope["raw_path"] = new_path.encode()
                updated_scope["root_path"] = (scope.get("root_path") or "") + self.prefix
                scope = updated_scope

        await self.app(scope, receive, send)
