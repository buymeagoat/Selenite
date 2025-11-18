"""Integration tests for authentication routes."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import hash_password


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpassword123"),
        )
        session.add(test_user)
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
            json={"username": "testuser", "password": "testpassword123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1440 * 60  # 24 hours in seconds


@pytest.mark.asyncio
async def test_login_invalid_username(test_db):
    """Test login with non-existent username."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_invalid_password(test_db):
    """Test login with incorrect password."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_validation_error(test_db):
    """Test login with invalid request format."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"username": "ab", "password": "short"},  # Too short
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_me_with_valid_token(test_db):
    """Test getting current user with valid token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
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
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert data["database"] == "healthy"
    assert "models" in data
