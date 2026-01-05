"""Unit tests for auth service helpers."""

from datetime import datetime, timezone

import pytest

from sqlalchemy import select

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
        user = await authenticate_user(session, "svc@example.com", "StrongPass123")
        assert user is not None
        assert user.username == "svcuser"


@pytest.mark.asyncio
async def test_authenticate_user_unknown_username():
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "missing@example.com", "StrongPass123")
        assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password():
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "svc@example.com", "WrongPass999")
        assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_disabled_behavior():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "svc@example.com"))
        user = result.scalar_one()
        user.is_disabled = True
        await session.commit()

    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, "svc@example.com", "StrongPass123")
        assert user is None

        user = await authenticate_user(
            session,
            "svc@example.com",
            "StrongPass123",
            include_disabled=True,
        )
        assert user is not None


def test_create_token_response_contains_expected_fields():
    issued_at = datetime.now(timezone.utc)
    user = User(
        id=1,
        username="admin",
        email="svc@example.com",
        is_admin=True,
        created_at=issued_at,
    )
    token = create_token_response(user)
    assert token.token_type == "bearer"
    assert token.expires_in == settings.access_token_expire_minutes * 60

    payload = decode_access_token(token.access_token)
    assert payload["user_id"] == 1
    assert payload["sub"] == "admin"
    assert token.user.username == "admin"
    assert token.user.is_admin is True
    assert token.user.created_at == issued_at
