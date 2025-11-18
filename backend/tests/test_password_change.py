"""Tests for password change endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password


@pytest.fixture
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            username="changepw",
            email="changepw@example.com",
            hashed_password=hash_password("originalPassword1"),
        )
        session.add(user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _login(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password_success(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "changepw", "originalPassword1")

        resp = await client.put(
            "/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "originalPassword1",
                "new_password": "newSecurePass2",
                "confirm_password": "newSecurePass2",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["detail"].lower().startswith("password changed")

        # Verify login works with new password and fails with old
        new_token_resp = await client.post(
            "/auth/login",
            json={"username": "changepw", "password": "newSecurePass2"},
        )
        assert new_token_resp.status_code == 200

        old_fail = await client.post(
            "/auth/login",
            json={"username": "changepw", "password": "originalPassword1"},
        )
        assert old_fail.status_code == 401


@pytest.mark.asyncio
async def test_change_password_incorrect_current(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "changepw", "originalPassword1")
        resp = await client.put(
            "/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongPassword",
                "new_password": "newSecurePass2",
                "confirm_password": "newSecurePass2",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Current password is incorrect"


@pytest.mark.asyncio
async def test_change_password_mismatch(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "changepw", "originalPassword1")
        resp = await client.put(
            "/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "originalPassword1",
                "new_password": "newSecurePass2",
                "confirm_password": "differentPass3",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Passwords do not match"


@pytest.mark.asyncio
async def test_change_password_reuse(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, "changepw", "originalPassword1")
        resp = await client.put(
            "/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "originalPassword1",
                "new_password": "originalPassword1",
                "confirm_password": "originalPassword1",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "New password must differ from current password"
