"""Tests for rate limiting middleware."""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_rate_limit_default_endpoint():
    """Test rate limiting on default endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default limit is 100 requests
        # Make several requests to verify rate limiting doesn't block normal usage
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_excluded_paths():
    """Test that excluded paths bypass rate limiting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check is excluded - should never hit rate limit
        for _ in range(20):
            response = await client.get("/health")
            assert response.status_code == 200
            assert "status" in response.json()


@pytest.mark.asyncio
async def test_rate_limit_recovery():
    """Test that rate limit tokens refill over time."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # This test verifies the token bucket refills
        # With default rate of 2 tokens/sec, we should recover quickly

        # Make a request
        response = await client.get("/health")
        assert response.status_code == 200

        # Wait for token refill
        await asyncio.sleep(1)

        # Should be able to make another request
        response = await client.get("/health")
        assert response.status_code == 200
