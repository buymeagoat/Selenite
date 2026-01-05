"""Tests for diagnostics routes."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password, create_access_token
from fastapi import status


@pytest.fixture
async def test_db():
    """Reset the database and seed admin user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        admin = User(
            id=1,
            username="admin",
            email="admin@selenite.local",
            hashed_password=hash_password("changeme"),
        )
        session.add(admin)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _auth_headers(user_id: int = 1, username: str = "admin") -> dict[str, str]:
    token = create_access_token({"sub": username, "user_id": user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_diagnostics_requires_auth(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/diagnostics/log", json={"level": "info", "message": "hi"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_diagnostics_log_with_auth(test_db):
    payload = {
        "level": "info",
        "message": "mobile test",
        "context": {"authorization": "secret", "note": "keep"},
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/diagnostics/log", json=payload, headers=_auth_headers())
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "logged"}


@pytest.mark.asyncio
async def test_diagnostics_info_sanitizes_headers(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/diagnostics/info",
            headers={**_auth_headers(), "x-request-id": "abc123", "user-agent": "pytest"},
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "headers" not in body
        assert body["request_id"] == "abc123"
        assert body["user_agent"] == "pytest"
