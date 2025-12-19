"""Integration tests for job management routes."""

import io
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.config import BACKEND_ROOT
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.job import Job
from app.models.tag import Tag
from app.utils.security import create_access_token, hash_password
from app.schemas.model_registry import ModelSetCreate, ModelWeightCreate
from app.services.model_registry import ModelRegistryService


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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

        # Seed a minimal ASR registry entry so jobs can be created
        models_root = BACKEND_ROOT / "models"
        set_path = models_root / "test-set"
        entry_path = set_path / "test-entry" / "model.bin"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("ok", encoding="utf-8")

        model_set = await ModelRegistryService.create_model_set(
            session,
            ModelSetCreate(type="asr", name="test-set", abs_path=str(set_path.resolve())),
            actor="system",
        )
        await ModelRegistryService.create_model_weight(
            session,
            model_set,
            ModelWeightCreate(
                name="test-entry",
                description="seed entry",
                abs_path=str(entry_path.resolve()),
                checksum=None,
            ),
            actor="system",
        )

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


async def _create_job_record(
    *,
    job_id: str,
    user_id: int = 1,
    status: str = "completed",
    file_path: str | None = None,
    transcript_path: str | None = None,
    original_filename: str = "sample.mp3",
):
    async with AsyncSessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=user_id,
            original_filename=original_filename,
            saved_filename=f"{job_id}.mp3",
            file_path=file_path or f"/tmp/{job_id}.mp3",
            file_size=1024,
            mime_type="audio/mpeg",
            status=status,
            progress_percent=0,
            model_used="test-entry",
            has_timestamps=True,
            has_speaker_labels=True,
            created_at=datetime.utcnow(),
            transcript_path=transcript_path,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def _create_tag_record(tag_id: int, name: str = "Tag", color: str = "#FF0000"):
    async with AsyncSessionLocal() as session:
        tag = Tag(id=tag_id, name=name, color=color)
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        return tag


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
            "model": "test-entry",
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
        completed = await _create_job_record(job_id=str(uuid4()), status="completed")
        await _create_job_record(job_id=str(uuid4()), status="failed")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs?status=completed", headers=auth_headers)
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total"] == 1
        assert json_data["items"][0]["id"] == completed.id

    async def test_list_jobs_filter_by_date_range(self, test_db, auth_headers):
        old_job = await _create_job_record(job_id=str(uuid4()))
        await _set_job_created_at(old_job.id, datetime.utcnow() - timedelta(days=7))
        recent = await _create_job_record(job_id=str(uuid4()))
        cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/jobs?date_from={cutoff}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == recent.id

    async def test_list_jobs_filter_by_tags(self, test_db, auth_headers):
        tag = await _create_tag_record(10, name="Finance")
        tagged = await _create_job_record(job_id=str(uuid4()))
        await _assign_tags_to_job(tagged.id, [tag.id])
        await _create_job_record(job_id=str(uuid4()))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs?tags=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == tagged.id

    async def test_list_jobs_filter_by_search(self, test_db, auth_headers):
        match = await _create_job_record(job_id=str(uuid4()), original_filename="Revenue_Q4.mp3")
        await _create_job_record(job_id=str(uuid4()), original_filename="standup.mp3")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs?search=Revenue", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == match.id

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
        data = {"model": "test-entry", "language": "en"}

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
        assert json_data["model_used"] == "test-entry"
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
        await session.refresh(job)
        return job


async def _assign_tags_to_job(job_id: str, tag_ids: list[int]):
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id, options=[selectinload(Job.tags)])
        tags = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        job.tags = tags.scalars().all()
        await session.commit()
        await session.refresh(job)


async def _set_job_created_at(job_id: str, created_at: datetime):
    await _update_job(job_id, created_at=created_at)


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

    async def test_cancel_queued_job_sets_cancelled(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(job_id, status="queued", progress_stage="waiting")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["progress_stage"] is None

    async def test_cancel_processing_job_sets_cancelling(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(job_id, status="processing", progress_stage="transcribing")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelling"
        assert data["progress_stage"] == "cancelling"

    async def test_cancel_non_cancellable_job(self, test_db, auth_headers):
        job_id = await _create_job_via_api(auth_headers)
        await _update_job(job_id, status="completed")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        assert response.status_code == 400
        assert "not cancellable" in response.json()["detail"]


@pytest.mark.asyncio
class TestJobTagAssignments:
    async def test_assign_tags_requires_list(self, test_db, auth_headers):
        job = await _create_job_record(job_id=str(uuid4()))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{job.id}/tags", json={"tag_ids": "oops"}, headers=auth_headers
            )
        assert response.status_code == 422

    async def test_assign_tags_empty_list(self, test_db, auth_headers):
        job = await _create_job_record(job_id=str(uuid4()))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{job.id}/tags", json={"tag_ids": []}, headers=auth_headers
            )
        assert response.status_code == 422

    async def test_assign_tags_job_not_found(self, test_db, auth_headers):
        transport = ASGITransport(app=app)
        missing_id = uuid4()
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{missing_id}/tags", json={"tag_ids": [1]}, headers=auth_headers
            )
        assert response.status_code == 404

    async def test_assign_tags_missing_tag_entries(self, test_db, auth_headers):
        job = await _create_job_record(job_id=str(uuid4()))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{job.id}/tags", json={"tag_ids": [123]}, headers=auth_headers
            )
        assert response.status_code == 404
        assert "One or more tags not found" in response.json()["detail"]

    async def test_assign_tags_success(self, test_db, auth_headers):
        job = await _create_job_record(job_id=str(uuid4()))
        tag1 = await _create_tag_record(1, name="Customer")
        tag2 = await _create_tag_record(2, name="Internal")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{job.id}/tags",
                json={"tag_ids": [tag1.id, tag2.id]},
                headers=auth_headers,
            )
        assert response.status_code == 200
        body = response.json()
        assert {tag["name"] for tag in body["tags"]} == {"Customer", "Internal"}
        # Verify persisted relationship
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Job).options(selectinload(Job.tags)).where(Job.id == job.id)
            )
            refreshed = result.scalar_one()
            assert len(refreshed.tags) == 2
