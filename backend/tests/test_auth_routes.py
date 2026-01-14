"""Integration tests for authentication routes."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from datetime import datetime, timedelta

from sqlalchemy import select

from app.utils.security import hash_password
from app.models.system_preferences import SystemPreferences


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test users
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpassword123"),
        )
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123"),
            is_admin=True,
        )
        prefs = await session.get(SystemPreferences, 1)
        if not prefs:
            prefs = SystemPreferences(id=1, session_timeout_minutes=30)
            session.add(prefs)
        else:
            prefs.session_timeout_minutes = 30

        session.add_all([test_user, admin_user])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_login_success(test_db):
    """Test successful login with valid credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 30 * 60


@pytest.mark.asyncio
async def test_login_sets_force_password_reset_for_policy_mismatch(test_db):
    async with AsyncSessionLocal() as session:
        prefs = await session.get(SystemPreferences, 1)
        prefs.password_min_length = 12
        prefs.password_require_uppercase = False
        prefs.password_require_lowercase = False
        prefs.password_require_number = False
        prefs.password_require_special = False
        session.add(
            User(
                username="legacyuser",
                email="legacy@example.com",
                hashed_password=hash_password("short1"),
            )
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "legacy@example.com", "password": "short1"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["force_password_reset"] is True


@pytest.mark.asyncio
async def test_login_invalid_username(test_db):
    """Test login with non-existent identifier."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_invalid_password(test_db):
    """Test login with incorrect password."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_validation_error(test_db):
    """Test login with invalid request format."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "ab", "password": "short"},  # Too short
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_me_with_valid_token(test_db):
    """Test getting current user with valid token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Get user info
        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_me_without_token(test_db):
    """Test getting current user without token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me")

    assert response.status_code == 403  # Forbidden (no credentials)


@pytest.mark.asyncio
async def test_get_me_with_invalid_token(test_db):
    """Test getting current user with invalid token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_get_me_invalid_token_payload(test_db, monkeypatch):
    """Decode returns payload without user_id -> invalid payload error."""
    monkeypatch.setattr("app.routes.auth.decode_access_token", lambda token: {})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token payload"


@pytest.mark.asyncio
async def test_get_me_user_not_found(test_db, monkeypatch):
    """Token references a user that no longer exists."""
    monkeypatch.setattr("app.routes.auth.decode_access_token", lambda token: {"user_id": 9999})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "0.1.0"
    assert data["environment"] in ["testing", "production"]
    assert data["database"] == "healthy"
    assert "models" in data


@pytest.mark.asyncio
async def test_session_timeout_enforced(test_db):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one()
        prefs.session_timeout_minutes = 1
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Age the session beyond the idle window
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == "test@example.com"))
            user = result.scalar_one()
            stale = datetime.utcnow() - timedelta(minutes=2)
            user.last_seen_at = stale
            user.last_login_at = stale
            await session.commit()

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Session timed out. Please log in again."


@pytest.mark.asyncio
async def test_restart_invalidation_enforced(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]

        # Raise auth_token_not_before beyond token iat
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemPreferences).where(SystemPreferences.id == 1)
            )
            prefs = result.scalar_one()
            prefs.auth_token_not_before = datetime.utcnow() + timedelta(seconds=10)
            await session.commit()

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Session expired. Please log in again."


@pytest.mark.asyncio
async def test_reset_sessions_requires_admin(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_response.json()["access_token"]
        response = await client.post(
            "/auth/reset-sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only admins may reset sessions."


@pytest.mark.asyncio
async def test_reset_sessions_bumps_not_before_and_invalidates_tokens(test_db):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one()
        before_reset = prefs.auth_token_not_before

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_login = await client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123"},
        )
        admin_token = admin_login.json()["access_token"]

        response = await client.post(
            "/auth/reset-sessions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Old token should now be invalid
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert me_response.status_code == 401

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one()
        assert prefs.auth_token_not_before is not None
        if before_reset is not None:
            assert prefs.auth_token_not_before >= before_reset


@pytest.mark.asyncio
async def test_signup_rejected_when_disabled(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/signup",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "StrongPass123",
            },
        )

    assert response.status_code == 403
    assert "signup" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signup_success_without_captcha_when_allowed(test_db):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one()
        prefs.allow_self_signup = True
        prefs.require_signup_captcha = False
        prefs.password_min_length = 8
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/signup",
            json={
                "username": "signupuser",
                "email": "signup@example.com",
                "password": "ValidPass123",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "signupuser"
    assert data["user"].get("is_email_verified") is True

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.email == "signup@example.com"))
        created = user_result.scalar_one()
        assert created.username == "signupuser"


@pytest.mark.asyncio
async def test_signup_enforces_password_policy(test_db):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one()
        prefs.allow_self_signup = True
        prefs.require_signup_captcha = False
        prefs.password_min_length = 14
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/signup",
            json={
                "username": "policyuser",
                "email": "policy@example.com",
                "password": "Short1234",
            },
        )

    assert response.status_code == 400
    assert "at least" in response.json()["detail"].lower()
