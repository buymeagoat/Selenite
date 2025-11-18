"""Tests for security headers middleware."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_present():
    """Test that security headers are added to responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        # Check for security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers


@pytest.mark.asyncio
async def test_csp_header_content():
    """Test Content-Security-Policy header configuration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        csp = response.headers["Content-Security-Policy"]

        # Verify key CSP directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_frame_options_deny():
    """Test X-Frame-Options is set to DENY."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_nosniff_header():
    """Test X-Content-Type-Options is set to nosniff."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
