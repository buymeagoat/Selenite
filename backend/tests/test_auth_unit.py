"""Direct unit tests for auth route helpers to tighten coverage."""

import pytest
from fastapi import HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.routes.auth import login, get_current_user, change_password
from app.schemas.auth import LoginRequest, PasswordChangeRequest
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password


@pytest.fixture(autouse=True)
async def setup_db():
    """Ensure a clean database with a single user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            id=1,
            username="unituser",
            email="unit@example.com",
            hashed_password=hash_password("UnitPass123"),
        )
        session.add(user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_login_invalid_credentials_direct():
    async with AsyncSessionLocal() as session:
        req = LoginRequest(username="missing", password="Nope1234")
        with pytest.raises(HTTPException) as exc:
            await login(req, db=session)
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_user(monkeypatch):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    monkeypatch.setattr("app.routes.auth.decode_access_token", lambda token: {"user_id": 999})
    async with AsyncSessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=creds, db=session)
        assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_change_password_direct_success(monkeypatch):
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User))).scalar_one()
        payload = PasswordChangeRequest(
            current_password="UnitPass123",
            new_password="BrandNewPass456",
            confirm_password="BrandNewPass456",
        )
        response = await change_password(payload, current_user=user, db=session)
        assert response.detail.startswith("Password changed")
