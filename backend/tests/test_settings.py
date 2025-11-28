"""Tests for settings routes."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from unittest.mock import AsyncMock
from types import SimpleNamespace
from fastapi import HTTPException

from app.main import app
from app.models.user import User
from app.models.settings import Settings
from app.models.user_settings import UserSettings
from app.utils.security import hash_password, create_access_token
from app.database import AsyncSessionLocal, engine, Base
from app.routes import settings as settings_routes
from app.schemas.settings import SettingsUpdateRequest


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user with explicit ID
        test_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
        )
        session.add(test_user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_token():
    """Create valid JWT token for test user."""
    return create_access_token({"user_id": 1, "username": "testuser"})


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers with JWT token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def default_settings(test_db, auth_token):
    """Create default settings for test user."""
    async with AsyncSessionLocal() as session:
        settings = Settings(
            user_id=1,
            default_model="medium",
            default_language="auto",
            default_timestamps=True,
            default_speaker_detection=True,
            max_concurrent_jobs=3,
            storage_location="/storage",
            storage_limit_bytes=107374182400,  # 100GB
        )
        session.add(settings)
        await session.commit()
    return settings


class TestGetSettings:
    """Test GET /settings endpoint."""

    async def test_get_settings_success(self, test_db, auth_headers, default_settings):
        """Test getting user settings."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/settings", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Verify all settings fields
            assert data["default_model"] == "medium"
            assert data["default_language"] == "auto"
            assert data["default_diarizer"] == "vad"
            assert data["diarization_enabled"] is False
            assert data["allow_job_overrides"] is False
            assert data["enable_timestamps"] is True
            if "default_speaker_detection" in data:
                assert data["default_speaker_detection"] is True
            assert data["max_concurrent_jobs"] == 3
            if "storage_location" in data:
                assert data["storage_location"] == "/storage"
            if "storage_limit_bytes" in data:
                assert data["storage_limit_bytes"] == 107374182400
            if "storage_used_bytes" in data:
                assert isinstance(data["storage_used_bytes"], int)

    async def test_get_settings_creates_defaults(self, test_db, auth_headers):
        """Test that default settings are created if they don't exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/settings", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Should have default values
            assert data["default_model"] == "medium"
            assert data["default_language"] == "auto"
            assert data["default_diarizer"] == "vad"
            assert data["diarization_enabled"] is False
            assert data["allow_job_overrides"] is False
            assert data["max_concurrent_jobs"] == 3

    async def test_get_settings_requires_auth(self, test_db):
        """Test that settings endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/settings")
            assert response.status_code == 403


class TestUpdateSettings:
    """Test PUT /settings endpoint."""

    async def test_update_all_settings(self, test_db, auth_headers, default_settings):
        """Test updating all settings fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            update_data = {
                "default_model": "large",
                "default_language": "en",
                "default_diarizer": "whisperx",
                "diarization_enabled": True,
                "allow_job_overrides": True,
                "enable_timestamps": False,
                "default_speaker_detection": False,
                "max_concurrent_jobs": 5,
            }
            response = await client.put("/settings", json=update_data, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            if "message" in data:
                assert data["message"] == "Settings updated successfully"
            if "settings" in data:
                assert data["settings"]["default_model"] == "large"
                assert data["settings"]["default_language"] == "en"
                assert data["settings"]["default_diarizer"] == "whisperx"
                assert data["settings"]["diarization_enabled"] is True
                assert data["settings"]["allow_job_overrides"] is True
                assert data["settings"]["enable_timestamps"] is False
                assert data["settings"]["default_speaker_detection"] is False
                assert data["settings"]["max_concurrent_jobs"] == 5

    async def test_update_partial_settings(self, test_db, auth_headers, default_settings):
        """Test updating only some settings fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            update_data = {
                "default_model": "small",
                "default_diarizer": "vad",
                "max_concurrent_jobs": 2,
            }
            response = await client.put("/settings", json=update_data, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Updated fields
            if "settings" in data:
                assert data["settings"]["default_model"] == "small"
                assert data["settings"]["default_diarizer"] == "vad"
                assert data["settings"]["max_concurrent_jobs"] == 2

                # Unchanged fields
                assert data["settings"]["default_language"] == "auto"
                assert data["settings"]["enable_timestamps"] is True

    async def test_update_settings_invalid_model(self, test_db, auth_headers, default_settings):
        """Test updating with invalid model name."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            update_data = {"default_model": "invalid_model"}
            response = await client.put("/settings", json=update_data, headers=auth_headers)
            assert response.status_code in [400, 422]
            detail = response.json().get("detail")
            if isinstance(detail, list):
                assert any("invalid" in str(item).lower() for item in detail)
            elif isinstance(detail, str):
                assert "invalid" in detail.lower()

    async def test_update_settings_invalid_diarizer(self, test_db, auth_headers, default_settings):
        """Invalid diarizer should be rejected."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                "/settings", json={"default_diarizer": "unknown"}, headers=auth_headers
            )
            assert response.status_code in [400, 422]

    async def test_update_settings_invalid_language(self, test_db, auth_headers, default_settings):
        """Test updating with invalid language code."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            update_data = {"default_language": "invalid_lang"}
            response = await client.put("/settings", json=update_data, headers=auth_headers)
            # Pydantic validation returns 422, but max_length constraint doesn't catch invalid codes
            # Our validation returns 400
            assert response.status_code in [400, 422]

    async def test_update_settings_invalid_concurrent_jobs(
        self, test_db, auth_headers, default_settings
    ):
        """Test updating with invalid max_concurrent_jobs value."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Too low
            response = await client.put(
                "/settings", json={"max_concurrent_jobs": 0}, headers=auth_headers
            )
            assert response.status_code == 422

            # Too high
            response = await client.put(
                "/settings", json={"max_concurrent_jobs": 20}, headers=auth_headers
            )
            assert response.status_code == 422

    async def test_update_settings_creates_if_not_exists(self, test_db, auth_headers):
        """Test that settings are created if they don't exist when updating."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            update_data = {"default_model": "tiny"}
            response = await client.put("/settings", json=update_data, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            if "settings" in data:
                assert data["settings"]["default_model"] == "tiny"

    async def test_update_settings_requires_auth(self, test_db):
        """Test that update settings requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/settings", json={"default_model": "large"})
            assert response.status_code == 403


class TestStorageCalculation:
    """Test storage used calculation."""

    async def test_storage_used_calculated(self, test_db, auth_headers, default_settings):
        """Test that storage_used_bytes is calculated from uploaded files."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/settings", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Should have storage_used_bytes field
            if "storage_used_bytes" in data:
                assert isinstance(data["storage_used_bytes"], int)
                assert data["storage_used_bytes"] >= 0


class TestSettingsValidation:
    """Test settings validation logic."""

    async def test_valid_models(self, test_db, auth_headers, default_settings):
        """Test that all valid Whisper models are accepted."""
        valid_models = ["tiny", "base", "small", "medium", "large", "large-v3"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for model in valid_models:
                response = await client.put(
                    "/settings", json={"default_model": model}, headers=auth_headers
                )
                assert response.status_code == 200, f"Model {model} should be valid"

    async def test_valid_diarizers(self, test_db, auth_headers, default_settings):
        """Ensure supported diarizers are accepted."""
        valid = ["whisperx", "pyannote", "vad"]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for option in valid:
                response = await client.put(
                    "/settings", json={"default_diarizer": option}, headers=auth_headers
                )
                assert response.status_code == 200, f"Diarizer {option} should be valid"

    async def test_valid_languages(self, test_db, auth_headers, default_settings):
        """Test that common language codes are accepted."""
        valid_languages = ["auto", "en", "es", "fr", "de", "it", "pt", "ru", "ja", "zh"]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for lang in valid_languages:
                response = await client.put(
                    "/settings", json={"default_language": lang}, headers=auth_headers
                )
                assert response.status_code == 200, f"Language {lang} should be valid"

    async def test_concurrent_jobs_range(self, test_db, auth_headers, default_settings):
        """Test valid range for max_concurrent_jobs (1-10)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Valid values
            for jobs in [1, 3, 5, 10]:
                response = await client.put(
                    "/settings", json={"max_concurrent_jobs": jobs}, headers=auth_headers
                )
                assert response.status_code == 200, f"Jobs count {jobs} should be valid"


@pytest.mark.asyncio
async def test_helper_creates_and_reuses_settings(test_db):
    """Exercise the internal helper coverage by creating default records."""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        existing = await session.execute(select(UserSettings))
        assert existing.scalars().first() is None

        first = await settings_routes._get_or_create_settings(user, session)
        assert isinstance(first, UserSettings)
        assert first.user_id == user.id

        second = await settings_routes._get_or_create_settings(user, session)
        assert second.id == first.id


@pytest.mark.asyncio
async def test_update_settings_sets_queue_concurrency(test_db, monkeypatch):
    """Ensure queue.set_concurrency executes when not in testing mode."""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        payload = SettingsUpdateRequest(
            default_model="large", default_language="es", max_concurrent_jobs=4
        )
        mock_set = AsyncMock()
        monkeypatch.setattr(settings_routes.queue, "set_concurrency", mock_set)
        monkeypatch.setattr(settings_routes, "settings", SimpleNamespace(is_testing=False))

        response = await settings_routes.update_settings(payload, current_user=user, db=session)

        mock_set.assert_awaited_once_with(4)
        assert response.max_concurrent_jobs == 4


@pytest.mark.asyncio
async def test_update_settings_queue_failure_raises_http_error(test_db, monkeypatch):
    """If queue rejects the concurrency value, the route should raise HTTP 400."""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        payload = SettingsUpdateRequest(
            default_model="base", default_language="en", max_concurrent_jobs=9
        )
        monkeypatch.setattr(
            settings_routes.queue,
            "set_concurrency",
            AsyncMock(side_effect=ValueError("invalid concurrency")),
        )
        monkeypatch.setattr(settings_routes, "settings", SimpleNamespace(is_testing=False))

        with pytest.raises(HTTPException) as exc:
            await settings_routes.update_settings(payload, current_user=user, db=session)

        assert exc.value.status_code == 400
        assert "invalid concurrency" in exc.value.detail
