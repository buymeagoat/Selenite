"""Tests for feedback submission routes."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.utils.security import hash_password, create_access_token
from app.database import AsyncSessionLocal, engine, Base


@pytest.fixture(scope="function")
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        admin = User(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("testpass123"),
            is_admin=True,
        )
        user = User(
            id=2,
            username="regular",
            email="user@example.com",
            hashed_password=hash_password("testpass123"),
            is_admin=False,
        )
        session.add_all([admin, user])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def admin_headers():
    token = create_access_token({"user_id": 1, "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers():
    token = create_access_token({"user_id": 2, "username": "regular"})
    return {"Authorization": f"Bearer {token}"}


class TestFeedbackSubmission:
    async def test_submit_feedback_requires_auth(self, test_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                data={"category": "bug", "message": "Something broke."},
            )
        assert response.status_code == 403

    async def test_submit_feedback_authenticated(self, test_db, user_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                headers=user_headers,
                data={"category": "suggestion", "message": "Please add dark mode."},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "suggestion"
        assert data["user_id"] == 2
        assert data["is_anonymous"] is False

    async def test_submit_feedback_with_attachment(self, test_db, user_headers):
        files = {
            "attachments": ("note.txt", b"hello", "text/plain"),
        }
        data = {"category": "comment", "message": "See attached."}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                headers=user_headers,
                data=data,
                files=files,
            )
        assert response.status_code == 201
        payload = response.json()
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["filename"] == "note.txt"


class TestFeedbackAdminAccess:
    async def test_list_feedback_requires_admin(self, test_db, user_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/feedback", headers=user_headers)
        assert response.status_code == 403

    async def test_list_feedback_admin(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/feedback",
                headers=admin_headers,
                data={"category": "bug", "message": "Report one."},
            )
            response = await client.get("/feedback", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_reply_requires_admin(self, test_db, user_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                headers=user_headers,
                data={
                    "category": "bug",
                    "message": "Report one.",
                    "submitter_email": "user@example.com",
                },
            )
            submission = response.json()
            reply = await client.post(
                f"/feedback/{submission['id']}/reply",
                headers=user_headers,
                json={"message": "Thanks"},
            )
        assert reply.status_code == 403

    async def test_reply_requires_smtp(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                headers=admin_headers,
                data={
                    "category": "comment",
                    "message": "Hello",
                    "submitter_email": "user@example.com",
                },
            )
            submission = response.json()
            reply = await client.post(
                f"/feedback/{submission['id']}/reply",
                headers=admin_headers,
                json={"message": "Thanks for the note"},
            )
        assert reply.status_code == 400

    async def test_delete_feedback(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                headers=admin_headers,
                data={"category": "bug", "message": "Delete me."},
            )
            submission = response.json()
            delete_response = await client.delete(
                f"/feedback/{submission['id']}", headers=admin_headers
            )
            list_response = await client.get("/feedback", headers=admin_headers)
        assert delete_response.status_code == 204
        assert list_response.status_code == 200
        assert list_response.json()["items"] == []
