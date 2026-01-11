"""Tests for HTTPS-only enforcement middleware."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.https_only import RequireHTTPSMiddleware


def _make_app(require_https: bool, allow_http_dev: bool, environment: str) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RequireHTTPSMiddleware,
        require_https=require_https,
        allow_http_dev=allow_http_dev,
        environment=environment,
    )

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_https_required_blocks_http():
    app = _make_app(require_https=True, allow_http_dev=False, environment="production")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://example.test") as client:
        response = await client.get("/ping")

    assert response.status_code == 426
    payload = response.json()
    assert payload["detail"] == "HTTPS is required"
    assert payload["upgrade_url"] == "https://example.test/ping"


@pytest.mark.asyncio
async def test_forwarded_proto_allows_https():
    app = _make_app(require_https=True, allow_http_dev=False, environment="production")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://example.test") as client:
        response = await client.get("/ping", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_allow_http_dev_in_development():
    app = _make_app(require_https=True, allow_http_dev=True, environment="development")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://example.test") as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
