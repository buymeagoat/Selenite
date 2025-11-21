"""Tests for rate limiting middleware."""

import asyncio
from typing import Iterable, Tuple

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request
from starlette.responses import Response

from app.main import app
from app.middleware.rate_limit import RateLimitMiddleware, RateLimiter, rate_limiter


def _build_request(
    path: str = "/health",
    method: str = "GET",
    headers: Iterable[Tuple[bytes, bytes]] | None = None,
    client_ip: str = "1.2.3.4",
) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "root_path": "",
        "headers": list(headers or []),
        "query_string": b"",
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.fixture
def reset_rate_limiter():
    """Ensure the global rate limiter does not leak state between tests."""
    rate_limiter._buckets.clear()
    rate_limiter._cleanup_counter = 0
    yield
    rate_limiter._buckets.clear()
    rate_limiter._cleanup_counter = 0


@pytest.mark.asyncio
async def test_rate_limit_default_endpoint():
    """Test rate limiting on default endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_excluded_paths():
    """Test that excluded paths bypass rate limiting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(20):
            response = await client.get("/health")
            assert response.status_code == 200
            assert "status" in response.json()


@pytest.mark.asyncio
async def test_rate_limit_recovery():
    """Test that rate limit tokens refill over time."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

        await asyncio.sleep(1)

        response = await client.get("/health")
        assert response.status_code == 200


def test_rate_limiter_consumes_and_refills(monkeypatch):
    """Directly exercise the token bucket mechanics."""
    limiter = RateLimiter()
    current_time = [1_000.0]

    def fake_time():
        return current_time[0]

    monkeypatch.setattr("app.middleware.rate_limit.time.time", fake_time)

    assert limiter.is_allowed("client", max_tokens=2, refill_rate=1.0)
    assert limiter.is_allowed("client", max_tokens=2, refill_rate=1.0)
    assert limiter.is_allowed("client", max_tokens=2, refill_rate=1.0) is False

    current_time[0] += 2.0
    assert limiter.is_allowed("client", max_tokens=2, refill_rate=1.0) is True


def test_rate_limit_middleware_client_key_selection():
    """_get_client_key should prioritize user, then forwarded header, then IP."""
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)

    request = _build_request("/jobs", client_ip="9.9.9.9")
    assert middleware._get_client_key(request) == "ip:9.9.9.9"

    request.state.user_id = 42
    assert middleware._get_client_key(request) == "user:42"

    forwarded_request = _build_request(
        "/jobs",
        headers=[(b"x-forwarded-for", b"10.0.0.1, 10.0.0.2")],
        client_ip="5.5.5.5",
    )
    assert middleware._get_client_key(forwarded_request) == "ip:10.0.0.1"


def test_rate_limit_middleware_limit_config():
    """Ensure special endpoint configs override the default."""
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    auth_config = middleware._get_limit_config("/auth/login", "POST")
    jobs_config = middleware._get_limit_config("/jobs/upload", "POST")
    default_config = middleware._get_limit_config("/search", "GET")

    assert auth_config["max_tokens"] == 5
    assert jobs_config["max_tokens"] == 10
    assert default_config["max_tokens"] == 100


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_after_threshold(reset_rate_limiter):
    """Rapid requests to auth endpoint should eventually hit the 429 guard."""
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)

    async def call_next(_request):
        return Response("ok")

    for _ in range(5):
        response = await middleware.dispatch(_build_request("/auth/login", "POST"), call_next)
        assert response.status_code == 200

    with pytest.raises(HTTPException) as exc:
        await middleware.dispatch(_build_request("/auth/login", "POST"), call_next)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_middleware_skips_excluded_paths(reset_rate_limiter):
    """Dispatch should immediately call the downstream app for excluded paths."""
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)

    async def call_next(_request):
        return Response("healthy", status_code=204)

    response = await middleware.dispatch(_build_request("/health", "GET"), call_next)
    assert response.status_code == 204
