"""Tests for transcript retrieval and export endpoints."""

import io
import asyncio
import os

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.config import settings
from app.models.user import User
from app.models.job import Job
from app.utils.security import create_access_token, hash_password
from app.services.job_queue import queue
from sqlalchemy import select


@pytest.fixture
async def test_db():
    """Create test database and ensure storage dirs."""
    os.makedirs(settings.media_storage_path, exist_ok=True)
    os.makedirs(settings.transcript_storage_path, exist_ok=True)

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

    # Ensure clean worker state per test: stop then start to bind to current loop
    if queue._started:
        try:
            await queue.stop()
        except Exception:
            # Force reset if prior loop was closed
            queue._workers.clear()
            queue._started = False
    await queue.start()

    # Give workers a moment to be ready
    await asyncio.sleep(0.1)

    yield

    # Stop workers to release DB connections
    if queue._started:
        try:
            await queue.stop()
        except Exception:
            pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def auth_headers():
    token = create_access_token(data={"user_id": 1, "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


async def wait_for_status(job_id: str, target_status: str, timeout: float = 6.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job_obj = result.scalar_one_or_none()
            if job_obj and job_obj.status == target_status:
                return job_obj
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"Timeout waiting for status {target_status}")
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
class TestTranscriptRoutes:
    async def test_get_transcript_and_export_all_formats(self, test_db, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create job
            files = {"file": ("meeting.mp3", io.BytesIO(b"fake audio"), "audio/mpeg")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            assert resp.status_code == 201
            job_id = resp.json()["id"]

            # Ensure enqueue on current loop's queue
            await queue.enqueue(job_id)

            # Wait for completion (simulated transcription)
            await wait_for_status(job_id, "completed", timeout=6.0)

            # GET transcript
            t_resp = await client.get(f"/transcripts/{job_id}", headers=auth_headers)
            assert t_resp.status_code == 200
            body = t_resp.json()
            assert body["job_id"] == job_id
            assert isinstance(body["text"], str) and len(body["text"]) > 0
            assert isinstance(body["segments"], list) and len(body["segments"]) >= 1
            assert "language" in body
            assert "duration" in body

            # Export in all formats
            formats = {
                "txt": "text/plain",
                "md": "text/markdown",
                "srt": "text/srt",
                "vtt": "text/vtt",
                "json": "application/json",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
            for fmt, ctype in formats.items():
                e_resp = await client.get(
                    f"/transcripts/{job_id}/export", params={"format": fmt}, headers=auth_headers
                )
                assert e_resp.status_code == 200
                assert e_resp.headers.get("content-type", "").startswith(ctype)
                # Content-Disposition filename
                cd = e_resp.headers.get("content-disposition", "")
                assert cd.startswith("attachment;") and f"-transcript.{fmt}" in cd
                assert e_resp.content and len(e_resp.content) > 0

    async def test_export_invalid_format(self, test_db, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("lecture.mp4", io.BytesIO(b"fake video"), "video/mp4")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            job_id = resp.json()["id"]

            await queue.enqueue(job_id)

            # Invalid format should return 400 regardless of job completion
            bad = await client.get(
                f"/transcripts/{job_id}/export", params={"format": "exe"}, headers=auth_headers
            )
            assert bad.status_code == 400
            assert "Invalid format" in bad.json()["detail"]
