"""Tests for admin user management routes."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.system_preferences import SystemPreferences
from app.models.user import User
from app.models.job import Job
from app.utils.security import hash_password, create_access_token
from sqlalchemy import select


@pytest.fixture
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        prefs = SystemPreferences(id=1)
        admin = User(
            username="admin",
            email=None,
            hashed_password=hash_password("changeme"),
            is_admin=True,
            is_disabled=False,
            force_password_reset=False,
        )
        user = User(
            username="user@example.com",
            email="user@example.com",
            hashed_password=hash_password("userpass123"),
            is_admin=False,
        )
        session.add_all([prefs, admin, user])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _auth_headers(user_id: int, username: str) -> dict[str, str]:
    token = create_access_token({"user_id": user_id, "sub": username})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_users_requires_admin(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/users", headers=_auth_headers(2, "user@example.com"))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_success(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/users", headers=_auth_headers(1, "admin"))

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_active_users_requires_admin(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/users/active", headers=_auth_headers(2, "user@example.com"))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_active_users_success(test_db):
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        admin = await session.get(User, 1)
        user = await session.get(User, 2)
        admin.last_seen_at = now
        user.last_seen_at = now - timedelta(minutes=2)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/users/active", headers=_auth_headers(1, "admin"))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert {item["username"] for item in data["items"]} >= {"admin", "user@example.com"}


@pytest.mark.asyncio
async def test_create_user_success(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/users",
            headers=_auth_headers(1, "admin"),
            json={"email": "newuser@example.com", "password": "StrongPass123", "is_admin": False},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["is_admin"] is False


@pytest.mark.asyncio
async def test_create_user_rejects_weak_password(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/users",
            headers=_auth_headers(1, "admin"),
            json={"email": "weak@example.com", "password": "weakpass", "is_admin": False},
        )

    assert response.status_code == 400
    assert "Password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_success(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/users/2",
            headers=_auth_headers(1, "admin"),
            json={"is_admin": True, "is_disabled": True, "force_password_reset": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["is_disabled"] is True
    assert data["force_password_reset"] is True


@pytest.mark.asyncio
async def test_update_user_rejects_weak_password(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/users/2",
            headers=_auth_headers(1, "admin"),
            json={"password": "weakpass"},
        )

    assert response.status_code == 400
    assert "Password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_root_admin_cannot_be_disabled(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/users/1",
            headers=_auth_headers(1, "admin"),
            json={"is_disabled": True},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Root admin cannot be disabled"


@pytest.mark.asyncio
async def test_delete_user_success(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/users/2", headers=_auth_headers(1, "admin"))

    assert response.status_code == 204

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == 2))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_user_blocks_active_jobs(test_db):
    async with AsyncSessionLocal() as session:
        session.add(
            Job(
                id="job-active",
                user_id=2,
                original_filename="file.wav",
                saved_filename="file.wav",
                file_path="storage/file.wav",
                status="processing",
            )
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/users/2", headers=_auth_headers(1, "admin"))

    assert response.status_code == 409
    assert "active jobs" in response.json()["detail"].lower()
