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


@pytest.mark.asyncio
class TestListJobs:
    """Tests for GET /jobs endpoint."""

    async def test_list_jobs_empty(self, test_db, auth_headers):
        """Test listing jobs when no jobs exist."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs", headers=auth_headers)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total"] == 0
        assert json_data["limit"] == 50
        assert json_data["offset"] == 0
        assert json_data["items"] == []

    async def test_list_jobs_with_data(self, test_db, auth_headers):
        """Test listing jobs with existing job data."""
        # Create a job first
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create job
            await client.post("/jobs", files=files, headers=auth_headers)

            # List jobs
            response = await client.get("/jobs", headers=auth_headers)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total"] == 1
        assert len(json_data["items"]) == 1
        assert json_data["items"][0]["original_filename"] == "test.mp3"
        assert json_data["items"][0]["status"] == "queued"

    async def test_list_jobs_pagination(self, test_db, auth_headers):
        """Test job listing with pagination."""
        # Create multiple jobs
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for i in range(5):
                file_content = b"fake audio content"
                files = {"file": (f"test{i}.mp3", io.BytesIO(file_content), "audio/mpeg")}
                await client.post("/jobs", files=files, headers=auth_headers)

            # Get first page (limit 2)
            response = await client.get("/jobs?limit=2&offset=0", headers=auth_headers)
            json_data = response.json()
            assert json_data["total"] == 5
            assert json_data["limit"] == 2
            assert json_data["offset"] == 0
            assert len(json_data["items"]) == 2

            # Get second page
            response = await client.get("/jobs?limit=2&offset=2", headers=auth_headers)
            json_data = response.json()
            assert json_data["total"] == 5
            assert json_data["offset"] == 2
            assert len(json_data["items"]) == 2

    async def test_list_jobs_filter_by_status(self, test_db, auth_headers):
        """Test filtering jobs by status."""
        # Create job
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/jobs", files=files, headers=auth_headers)

            # Filter by queued status
            response = await client.get("/jobs?status=queued", headers=auth_headers)
            json_data = response.json()
            assert json_data["total"] == 1
            assert json_data["items"][0]["status"] == "queued"

            # Filter by completed status (should be empty)
            response = await client.get("/jobs?status=completed", headers=auth_headers)
            json_data = response.json()
            assert json_data["total"] == 0

    async def test_list_jobs_no_authentication(self):
        """Test that job listing requires authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs")

        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetJob:
    """Tests for GET /jobs/{job_id} endpoint."""

    async def test_get_job_success(self, test_db, auth_headers):
        """Test retrieving a single job by ID."""
        # Create a job first
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        data = {"model": "medium", "language": "en"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create job
            create_response = await client.post(
                "/jobs", files=files, data=data, headers=auth_headers
            )
            job_id = create_response.json()["id"]

            # Get job by ID
            response = await client.get(f"/jobs/{job_id}", headers=auth_headers)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["id"] == job_id
        assert json_data["original_filename"] == "test.mp3"
        assert json_data["status"] == "queued"
        assert json_data["model_used"] == "medium"
        assert "file_path" in json_data
        assert "saved_filename" in json_data
        assert "available_exports" in json_data

    async def test_get_job_not_found(self, test_db, auth_headers):
        """Test retrieving non-existent job returns 404."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/jobs/{fake_uuid}", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_job_invalid_uuid(self, test_db, auth_headers):
        """Test retrieving job with invalid UUID format."""
        invalid_uuid = "not-a-valid-uuid"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/jobs/{invalid_uuid}", headers=auth_headers)

        assert response.status_code == 422  # Validation error

    async def test_get_job_no_authentication(self, test_db):
        """Test that job retrieval requires authentication."""
        # Create a job first (with auth)
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        auth_token = create_access_token(data={"user_id": 1, "username": "admin"})
        auth_headers = {"Authorization": f"Bearer {auth_token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post("/jobs", files=files, headers=auth_headers)
            job_id = create_response.json()["id"]

            # Try to get job without auth
            response = await client.get(f"/jobs/{job_id}")

        assert response.status_code == 403
