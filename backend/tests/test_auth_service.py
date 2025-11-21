"""Unit tests for auth service helpers."""

import pytest

from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.services.auth import authenticate_user, create_token_response
from app.utils.security import hash_password, decode_access_token
from app.config import settings


@pytest.fixture(autouse=True)
async def setup_db():
    """Create/drop schema around each test with a default user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            username="svcuser",
            email="svc@example.com",
            hashed_password=hash_password("StrongPass123"),
        )
        session.add(user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_authenticate_user_success():
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "svcuser", "StrongPass123")
        assert user is not None
        assert user.username == "svcuser"


@pytest.mark.asyncio
async def test_authenticate_user_unknown_username():
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "missing", "StrongPass123")
        assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password():
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "svcuser", "WrongPass999")
        assert user is None


def test_create_token_response_contains_expected_fields():
    user = User(id=42, username="svcuser", email="svc@example.com")
    token = create_token_response(user)
    assert token.token_type == "bearer"
    assert token.expires_in == settings.access_token_expire_minutes * 60

    payload = decode_access_token(token.access_token)
    assert payload["user_id"] == 42
    assert payload["sub"] == "svcuser"
