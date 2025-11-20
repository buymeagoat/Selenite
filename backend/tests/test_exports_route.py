"""Tests for transcript export route."""

import json
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.job import Job
from app.utils.security import hash_password, create_access_token


@pytest.fixture
async def test_db():
    """Create all tables and seed two users."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user1 = User(
            id=1,
            username="exporter",
            email="exporter@example.com",
            hashed_password=hash_password("changeme"),
        )
        user2 = User(
            id=2,
            username="intruder",
            email="intruder@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add_all([user1, user2])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_headers_user1():
    token = create_access_token({"user_id": 1, "username": "exporter"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2():
    token = create_access_token({"user_id": 2, "username": "intruder"})
    return {"Authorization": f"Bearer {token}"}


async def _create_job(
    *,
    job_id: str,
    user_id: int,
    status: str,
    transcript_path: Path | None,
    original_filename: str = "sample-audio.mp3",
):
    async with AsyncSessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=user_id,
            original_filename=original_filename,
            saved_filename=f"{job_id}.mp3",
            file_path=f"/tmp/{job_id}.mp3",
            file_size=1024,
            mime_type="audio/mpeg",
            status=status,
            transcript_path=str(transcript_path) if transcript_path else None,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


@pytest.mark.anyio
async def test_export_txt_success(tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("Hello world", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text(json.dumps({"segments": [{"text": "Hello world"}]}))
    job = await _create_job(
        job_id="job-success",
        user_id=1,
        status="completed",
        transcript_path=transcript,
        original_filename="meeting_recording.mp3",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export?format=txt", headers=auth_headers_user1)

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="meeting_recording.txt"'
    )
    assert response.text == "Hello world"


@pytest.mark.anyio
async def test_export_invalid_format(test_db, auth_headers_user1):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/jobs/some-job/export?format=pdf", headers=auth_headers_user1)
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


@pytest.mark.anyio
async def test_export_job_not_found(test_db, auth_headers_user1):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/jobs/missing/export", headers=auth_headers_user1)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_export_unauthorized_user(tmp_path, test_db, auth_headers_user2):
    transcript = tmp_path / "secret.txt"
    transcript.write_text("secret", encoding="utf-8")
    job = await _create_job(
        job_id="job-secret",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export", headers=auth_headers_user2)
    assert response.status_code == 403


@pytest.mark.anyio
async def test_export_not_completed_job(tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "pending.txt"
    transcript.write_text("pending", encoding="utf-8")
    job = await _create_job(
        job_id="job-pending",
        user_id=1,
        status="processing",
        transcript_path=transcript,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export", headers=auth_headers_user1)
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]


@pytest.mark.anyio
async def test_export_missing_transcript(tmp_path, test_db, auth_headers_user1):
    job = await _create_job(
        job_id="job-missing-tx",
        user_id=1,
        status="completed",
        transcript_path=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export", headers=auth_headers_user1)
    assert response.status_code == 404
    assert "Transcript file not found" in response.json()["detail"]
