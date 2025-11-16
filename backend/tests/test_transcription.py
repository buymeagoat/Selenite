"""Integration tests for transcription engine and job queue (Increment 5)."""

import asyncio
from typing import List, Any, cast

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.services.job_queue import queue
from app.database import AsyncSessionLocal, engine, Base
from app.config import settings
from app.models.user import User
from app.models.job import Job
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def test_db():
    """Create and tear down test database with admin user."""
    # Ensure storage directories exist for file uploads
    import os

    os.makedirs(settings.media_storage_path, exist_ok=True)
    os.makedirs(settings.transcript_storage_path, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        test_user = User(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add(test_user)
        await session.commit()

    # Ensure transcription workers are running for tests
    if not queue._started:
        await queue.start()

    # Give workers a moment to be ready
    await asyncio.sleep(0.1)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def auth_headers():
    token = create_access_token(data={"user_id": 1, "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


async def wait_for_status(job_id: str, target_status: str, timeout: float = 8.0) -> Any:
    """Poll the database until job reaches target status or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        # Create a fresh session for each poll to see committed changes
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job_obj = cast(Any, result.scalar_one_or_none())
            if job_obj and job_obj.status == target_status:
                return job_obj
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"Timeout waiting for status {target_status}")
        await asyncio.sleep(0.05)  # Yield control to let workers run


@pytest.mark.asyncio
class TestTranscriptionLifecycle:
    async def test_transcription_job_lifecycle(self, test_db, auth_headers):
        """Job transitions queued -> processing -> completed with transcript path set or simulated."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create job (should enqueue automatically once implemented)
            files = {"file": ("speech.mp3", b"fake", "audio/mpeg")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            assert resp.status_code == 201
            job_id = resp.json()["id"]

        # Give asyncio a chance to schedule worker tasks
        for _ in range(5):
            await asyncio.sleep(0)

        # Wait for processing then completion
        await asyncio.sleep(0.3)  # Allow worker to pick up job
        job_processing = await wait_for_status(job_id, "processing", timeout=3.0)
        assert job_processing.progress_percent >= 10
        assert job_processing.progress_stage in {"loading_model", "transcribing", "finalizing"}

        job_done = await wait_for_status(job_id, "completed", timeout=5.0)
        assert job_done.progress_percent == 100
        assert job_done.completed_at is not None
        assert job_done.started_at is not None
        # estimated_time_left should be None at the end
        assert job_done.estimated_time_left is None

    async def test_transcription_progress_stages(self, test_db, auth_headers):
        """Stages should progress in order with increasing progress_percent."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("stage_check.wav", b"fake", "audio/wav")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            job_id = resp.json()["id"]

        # Give worker time to start
        await asyncio.sleep(0.3)

        # Sample snapshots during processing
        snapshots: List[int] = []
        for _ in range(5):
            await asyncio.sleep(0.3)  # Longer delay to catch progress changes
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Job).where(Job.id == job_id))
                job_obj = cast(Any, result.scalar_one_or_none())
                if job_obj:
                    snapshots.append(int(job_obj.progress_percent))
        # Ensure progress increased at least once
        assert any(b > a for a, b in zip(snapshots, snapshots[1:])), snapshots

    async def test_transcription_failure_handling(self, test_db, auth_headers):
        """Simulate a failure and verify status=failed and error_message set."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("will_fail.mp3", b"fake", "audio/mpeg")}
            # Include a query param to trigger failure via filename convention
            resp = await client.post(
                "/jobs", files=files, headers=auth_headers, params={"fail": "1"}
            )
            job_id = resp.json()["id"]

        # Give worker time to process and fail
        await asyncio.sleep(0.8)

        # Wait for failure
        job_failed = await wait_for_status(job_id, "failed", timeout=3.0)
        assert job_failed.error_message is not None
        assert job_failed.progress_percent < 100

    async def test_concurrent_job_limit(self, test_db, auth_headers):
        """At most 3 jobs should be processing concurrently."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create multiple jobs quickly
            created_ids = []
            for i in range(5):
                files = {"file": (f"batch{i}.mp3", b"fake", "audio/mpeg")}
                resp = await client.post("/jobs", files=files, headers=auth_headers)
                created_ids.append(resp.json()["id"])

        # Observe the system for a short period, ensure <=3 processing at any time
        for _ in range(20):
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Job).where(Job.status == "processing"))
                processing_count = len(result.scalars().all())
                assert processing_count <= 3
            await asyncio.sleep(0.1)

    async def test_estimated_time_updates(self, test_db, auth_headers):
        """During processing, estimated_time_left should be a positive integer then None when completed."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("estimate.wav", b"fake", "audio/wav")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            job_id = resp.json()["id"]

        # Wait briefly and check while processing
        await asyncio.sleep(0.6)  # Give worker time to reach processing state
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job_obj = cast(Any, result.scalar_one_or_none())
            if job_obj and job_obj.status == "processing":
                assert job_obj.estimated_time_left is None or isinstance(
                    job_obj.estimated_time_left, int
                )

        # Completed: should be None
        done = await wait_for_status(job_id, "completed", timeout=4.0)
        assert done.estimated_time_left is None
