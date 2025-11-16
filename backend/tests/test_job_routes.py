"""Integration tests for job management routes."""

import io

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user
        test_user = User(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add(test_user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def auth_token():
    """Generate a valid JWT token for test user."""
    token = create_access_token(data={"user_id": 1, "username": "admin"})
    return token


@pytest.fixture
async def auth_headers(auth_token):
    """Generate authorization headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.mark.asyncio
class TestCreateJob:
    """Tests for POST /jobs endpoint."""

    async def test_create_job_success(self, test_db, auth_headers):
        """Test successful job creation with valid file upload."""
        # Create fake audio file
        file_content = b"fake audio content for testing"
        files = {"file": ("test_audio.mp3", io.BytesIO(file_content), "audio/mpeg")}

        # Form data
        data = {
            "model": "medium",
            "language": "auto",
            "enable_timestamps": "true",
            "enable_speaker_detection": "true",
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data, headers=auth_headers)

        assert response.status_code == 201
        json_data = response.json()
        assert "id" in json_data
        assert json_data["original_filename"] == "test_audio.mp3"
        assert json_data["status"] == "queued"
        assert "created_at" in json_data

    async def test_create_job_with_different_models(self, test_db, auth_headers):
        """Test job creation with different Whisper models."""
        models = ["tiny", "base", "small", "medium", "large"]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for model in models:
                file_content = b"fake audio content"
                files = {
                    "file": (
                        f"test_{model}.mp3",
                        io.BytesIO(file_content),
                        "audio/mpeg",
                    )
                }
                data = {"model": model}

                response = await client.post("/jobs", files=files, data=data, headers=auth_headers)

                assert response.status_code == 201

    async def test_create_job_invalid_file_format(self, test_db, auth_headers):
        """Test that invalid file formats are rejected."""
        file_content = b"not really a PDF but pretending"
        files = {"file": ("document.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"model": "medium"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data, headers=auth_headers)

        assert response.status_code == 400
        assert "Invalid file format" in response.json()["detail"]

    async def test_create_job_missing_file(self, test_db, auth_headers):
        """Test that missing file is rejected."""
        data = {"model": "medium"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", data=data, headers=auth_headers)

        assert response.status_code == 422  # Validation error

    async def test_create_job_no_authentication(self):
        """Test that job creation requires authentication."""
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        data = {"model": "medium"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data)

        assert response.status_code == 403  # Forbidden (no auth)

    async def test_create_job_invalid_token(self):
        """Test that invalid token is rejected."""
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        data = {"model": "medium"}
        headers = {"Authorization": "Bearer invalid_token_here"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data, headers=headers)

        assert response.status_code == 401  # Unauthorized

    async def test_create_job_default_values(self, test_db, auth_headers):
        """Test that default values are applied when not specified."""
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        # Don't provide model or options - should use defaults

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, headers=auth_headers)

        assert response.status_code == 201
        # Job should be created with default model="medium"

    async def test_create_job_with_video_file(self, test_db, auth_headers):
        """Test job creation with video file."""
        file_content = b"fake video content"
        files = {"file": ("video.mp4", io.BytesIO(file_content), "video/mp4")}
        data = {"model": "small"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data, headers=auth_headers)

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["original_filename"] == "video.mp4"

    async def test_create_job_options(self, test_db, auth_headers):
        """Test job creation with all options specified."""
        file_content = b"fake audio content"
        files = {"file": ("lecture.wav", io.BytesIO(file_content), "audio/wav")}
        data = {
            "model": "large",
            "language": "en",
            "enable_timestamps": "false",
            "enable_speaker_detection": "false",
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, data=data, headers=auth_headers)

        assert response.status_code == 201
