"""Tests for system restart/shutdown routes."""

import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.routes import system as system_module
from app.utils.security import hash_password, create_access_token


@pytest.fixture
async def test_db():
    """Reset DB and seed admin plus normal user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        admin = User(
            id=1,
            username="admin",
            email="admin@selenite.local",
            hashed_password=hash_password("changeme"),
            is_admin=True,
        )
        user = User(
            id=2,
            username="member",
            email="member@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add_all([admin, user])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _auth_headers(user_id: int, username: str) -> dict[str, str]:
    token = create_access_token({"sub": username, "user_id": user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_restart_blocks_non_admin(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/system/restart", headers=_auth_headers(2, "member"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_restart_triggers_script(monkeypatch, test_db):
    invoked = []

    def fake_schedule(action: str, script_name: str) -> None:
        invoked.append((action, script_name))

    monkeypatch.setattr(system_module, "_schedule_script", fake_schedule)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/system/restart", headers=_auth_headers(1, "admin"))

    assert resp.status_code == status.HTTP_200_OK
    assert invoked == [("restart", "restart-selenite.ps1")]


@pytest.mark.asyncio
async def test_shutdown_triggers_script(monkeypatch, test_db):
    invoked = []

    def fake_schedule(action: str, script_name: str) -> None:
        invoked.append((action, script_name))

    monkeypatch.setattr(system_module, "_schedule_script", fake_schedule)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/system/shutdown", headers=_auth_headers(1, "admin"))

    assert resp.status_code == status.HTTP_200_OK
    assert invoked == [("shutdown", "stop-selenite.ps1")]
