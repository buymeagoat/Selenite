"""Tests for audit log routes."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def test_db():
    """Reset DB and seed admin + member plus audit entries."""
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
        member = User(
            id=2,
            username="member",
            email="member@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add_all([admin, member])
        await session.flush()

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                AuditLog(
                    actor_user_id=admin.id,
                    action="user.created",
                    target_type="user",
                    target_id=str(member.id),
                    ip_address="127.0.0.1",
                    created_at=now - timedelta(minutes=5),
                ),
                AuditLog(
                    actor_user_id=member.id,
                    action="auth.login",
                    target_type="session",
                    target_id="token-1",
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _auth_headers(user_id: int, username: str) -> dict[str, str]:
    token = create_access_token({"sub": username, "user_id": user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_audit_logs_requires_admin(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/audit-logs", headers=_auth_headers(2, "member"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        resp = await client.get("/audit-logs/export", headers=_auth_headers(2, "member"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_audit_logs_list_and_filter(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/audit-logs", headers=_auth_headers(1, "admin"))
        assert resp.status_code == status.HTTP_200_OK
        payload = resp.json()
        assert payload["total"] == 2
        assert len(payload["items"]) == 2

        resp = await client.get(
            "/audit-logs",
            headers=_auth_headers(1, "admin"),
            params={"action": "user.created"},
        )
        assert resp.status_code == status.HTTP_200_OK
        payload = resp.json()
        assert payload["total"] == 1
        assert payload["items"][0]["action"] == "user.created"


@pytest.mark.asyncio
async def test_audit_logs_export_csv(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/audit-logs/export", headers=_auth_headers(1, "admin"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"].startswith("text/csv")
        text = resp.text
        assert "id,created_at,action" in text
