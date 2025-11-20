"""Integration tests for job management routes."""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.job import Job
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

    # Rate limit test removed as requested. Invalid file format test no longer asserts rate limit errors.

    async def test_create_job_invalid_format(self, test_db, auth_headers):
        """Uploading an unsupported file extension should fail."""
        file_content = b"not audio"
        files = {"file": ("bad.txt", io.BytesIO(file_content), "text/plain")}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "file type" in response.json()["detail"]

    async def test_create_job_without_auth(self, test_db):
        """Request must include auth header."""
        file_content = b"fake audio content"
        files = {"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files)
        assert response.status_code in {401, 403}

    async def test_create_job_default_values(self, test_db, auth_headers):
        """Omitting optional form fields should fall back to defaults."""
        file_content = b"fake audio content"
        files = {"file": ("default.mp3", io.BytesIO(file_content), "audio/mpeg")}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs", files=files, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "default.mp3"
        assert data["status"] == "queued"


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

    async def test_list_jobs_with_data(self, test_db, auth_headers):
        """List endpoint returns created jobs with pagination metadata."""
        file_content = b"fake audio content"
        files = {"file": ("a.mp3", io.BytesIO(file_content), "audio/mpeg")}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/jobs", files=files, headers=auth_headers)
            await client.post(
                "/jobs",
                files={"file": ("b.mp3", io.BytesIO(file_content), "audio/mpeg")},
                headers=auth_headers,
            )
            response = await client.get("/jobs?limit=10&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


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


async def _create_job_via_api(auth_headers: dict, filename: str = "test.mp3") -> str:
    """Helper to create a job through the API and return its ID."""
    file_content = b"fake audio content"
    files = {"file": (filename, io.BytesIO(file_content), "audio/mpeg")}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/jobs", files=files, headers=auth_headers)
    assert response.status_code == 201
    return response.json()["id"]


async def _update_job(job_id: str, **fields):
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        for key, value in fields.items():
            setattr(job, key, value)
        await session.commit()


@pytest.mark.asyncio
class TestJobLifecycleActions:
    async def test_restart_completed_job_creates_new_job(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(
            job_id,
            status="completed",
            completed_at=None,
            file_size=1234,
            file_path="/tmp/test.mp3",
            model_used="base",
        )
        with patch("app.routes.jobs.queue.enqueue", new=AsyncMock()) as mock_enqueue:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/jobs/{job_id}/restart", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        mock_enqueue.assert_awaited_once()

    async def test_restart_active_job_rejected(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(job_id, status="processing")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/jobs/{job_id}/restart", headers=auth_headers)
        assert response.status_code == 400
        assert "Cannot restart an active job" in response.json()["detail"]

    async def test_delete_processing_job_forbidden(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(job_id, status="processing")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 400
        assert "Cancel it first" in response.json()["detail"]

    async def test_delete_completed_job_removes_files(self, tmp_path, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        media_path = tmp_path / "media.mp3"
        media_path.write_bytes(b"content")
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("hello", encoding="utf-8")
        await _update_job(
            job_id,
            status="completed",
            file_path=str(media_path),
            transcript_path=str(transcript_path),
            model_used="base",
            mime_type="audio/mpeg",
        )
        assert media_path.exists()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 204
        assert not media_path.exists()
