"""Tests for admin messages routes."""

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
        session.add(admin)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def admin_headers():
    token = create_access_token({"user_id": 1, "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


class TestMessagesAdmin:
    async def test_create_draft_and_list(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/messages/drafts",
                headers=admin_headers,
                data={"subject": "Draft", "message": "Hold this."},
            )
            assert response.status_code == 200
            draft = response.json()
            assert draft["folder"] == "drafts"

            list_response = await client.get(
                "/messages",
                headers=admin_headers,
                params={"folder": "drafts"},
            )
            assert list_response.status_code == 200
            payload = list_response.json()
            assert payload["total"] == 1

    async def test_delete_message_moves_to_deleted(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create = await client.post(
                "/messages/drafts",
                headers=admin_headers,
                data={"subject": "Draft", "message": "Delete me."},
            )
            message_id = create.json()["id"]
            delete_resp = await client.post(f"/messages/{message_id}/delete", headers=admin_headers)
            assert delete_resp.status_code == 200
            assert delete_resp.json()["folder"] == "deleted"

    async def test_send_message_requires_smtp(self, test_db, admin_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/messages/send",
                headers=admin_headers,
                data={"recipient_email": "user@example.com", "message": "Hello"},
            )
            assert response.status_code == 400
