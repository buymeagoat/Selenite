"""Unit tests for TranscriptionJobQueue internals."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.services.job_queue import (
    TranscriptionJobQueue,
    resolve_queue_concurrency,
    finalize_incomplete_jobs,
)
import app.services.job_queue as job_queue_module
from app.database import AsyncSessionLocal, engine, Base
from app.models.job import Job
from app.models.user import User
from app.models.user_settings import UserSettings


class DummySession:
    """AsyncSession stub used to avoid touching the real database."""

    def __init__(self):
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_enqueue_processes_job_once(monkeypatch):
    """Ensure enqueue triggers process_transcription_job exactly once per ID."""
    calls: list[tuple[str, bool]] = []

    async def fake_process(job_id, db, should_fail=False):
        calls.append((job_id, should_fail))

    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(job_queue_module, "process_transcription_job", fake_process)

    queue = TranscriptionJobQueue(concurrency=1)
    await queue.start()

    await queue.enqueue("job-1")
    assert queue._queue is not None
    await asyncio.wait_for(queue._queue.join(), timeout=1)

    assert calls == [("job-1", False)]

    # Mark running to simulate in-flight job; enqueue should no-op.
    queue._running_ids.add("job-1")
    await queue.enqueue("job-1")
    assert queue._queue.qsize() == 0
    queue._running_ids.clear()

    await queue.stop()


@pytest.mark.asyncio
async def test_enqueue_skips_when_testing(monkeypatch):
    """When not started and settings.is_testing is True, enqueue should no-op."""
    queue = TranscriptionJobQueue()
    monkeypatch.setattr(job_queue_module, "settings", SimpleNamespace(is_testing=True))

    await queue.enqueue("job-x")

    assert queue._queue is None
    assert not queue._started


@pytest.mark.asyncio
async def test_enqueue_autostarts_when_not_testing(monkeypatch):
    """Enqueue should spawn workers when not testing."""
    queue = TranscriptionJobQueue()
    monkeypatch.setattr(job_queue_module, "settings", SimpleNamespace(is_testing=False))
    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())

    async def fake_process(job_id, db, should_fail=False):
        return None

    monkeypatch.setattr(job_queue_module, "process_transcription_job", fake_process)

    await queue.enqueue("auto-job")
    assert queue._started is True
    assert queue._queue is not None
    await asyncio.wait_for(queue._queue.join(), timeout=1)
    await queue.stop()


@pytest.mark.asyncio
async def test_set_concurrency_restarts_workers(monkeypatch):
    """Changing concurrency restarts workers and updates worker count."""
    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        job_queue_module, "process_transcription_job", lambda *args, **kwargs: asyncio.sleep(0)
    )

    queue = TranscriptionJobQueue(concurrency=1)
    await queue.start()
    assert len(queue._workers) == 1

    await queue.set_concurrency(2)
    assert queue._concurrency == 2
    assert len(queue._workers) == 2

    await queue.stop()


@pytest.mark.asyncio
async def test_set_concurrency_rejects_invalid():
    """Concurrency must be >=1."""
    queue = TranscriptionJobQueue()
    with pytest.raises(ValueError):
        await queue.set_concurrency(0)


@pytest.mark.asyncio
async def test_stop_handles_event_loop_closed(monkeypatch):
    """Simulate RuntimeError during stop to hit defensive branch."""
    queue = TranscriptionJobQueue()

    class FakeQueue:
        async def put(self, item):
            raise RuntimeError("Event loop is closed")

    queue._queue = FakeQueue()
    queue._workers = [object(), object()]

    async def fake_gather(*args, **kwargs):
        return None

    monkeypatch.setattr(asyncio, "gather", fake_gather)
    await queue.stop()
    assert queue._queue is None


@pytest.mark.asyncio
async def test_set_concurrency_handles_loop_closed(monkeypatch):
    """If stop raises RuntimeError loop closed, state should reset."""
    queue = TranscriptionJobQueue(concurrency=1)

    async def fake_stop():
        raise RuntimeError("Event loop is closed")

    queue.stop = fake_stop  # type: ignore[assignment]

    def raise_runtime():
        raise RuntimeError("no loop")

    monkeypatch.setattr("asyncio.get_running_loop", raise_runtime)
    await queue.set_concurrency(2)
    assert queue._started is False
    assert queue._queue is None


@pytest.mark.asyncio
async def test_resume_queued_jobs_requeues_pending(monkeypatch):
    """resume_queued_jobs should enqueue every job still marked queued."""
    user_id = None
    queued_id = str(uuid4())
    completed_id = str(uuid4())

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        suffix = uuid4().hex[:8]
        user = User(
            username=f"queue_user_{suffix}",
            email=f"queue_user_{suffix}@example.com",
            hashed_password="hashed",
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        session.add_all(
            [
                Job(
                    id=queued_id,
                    user_id=user_id,
                    original_filename="queued.mp3",
                    saved_filename="queued.mp3",
                    file_path=f"/tmp/{queued_id}.mp3",
                    file_size=1234,
                    mime_type="audio/mpeg",
                    status="queued",
                    progress_percent=0,
                    model_used="medium",
                    has_timestamps=True,
                    has_speaker_labels=True,
                    created_at=datetime.utcnow(),
                ),
                Job(
                    id=completed_id,
                    user_id=user_id,
                    original_filename="done.mp3",
                    saved_filename="done.mp3",
                    file_path=f"/tmp/{completed_id}.mp3",
                    file_size=4321,
                    mime_type="audio/mpeg",
                    status="completed",
                    progress_percent=100,
                    model_used="medium",
                    has_timestamps=True,
                    has_speaker_labels=True,
                    created_at=datetime.utcnow(),
                ),
            ]
        )
        await session.commit()

    enqueued: list[tuple[str, bool]] = []

    class StubQueue:
        async def enqueue(self, job_id: str, *, should_fail: bool = False):
            enqueued.append((job_id, should_fail))

    try:
        await job_queue_module.resume_queued_jobs(StubQueue())  # type: ignore[arg-type]
        assert any(item[0] == queued_id for item in enqueued)
        assert all(item[0] != completed_id for item in enqueued)
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Job).where(Job.id.in_([queued_id, completed_id])))
            if user_id is not None:
                await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_resolve_queue_concurrency_prefers_admin():
    """Startup concurrency should prefer admin user settings when present."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with AsyncSessionLocal() as session:
            admin = User(username="admin", email="admin@selenite.local", hashed_password="hashed")
            other = User(username="member", email="member@example.com", hashed_password="hashed")
            session.add_all([admin, other])
            await session.flush()
            session.add_all(
                [
                    UserSettings(user_id=admin.id, max_concurrent_jobs=1),
                    UserSettings(user_id=other.id, max_concurrent_jobs=5),
                ]
            )
            await session.commit()

            value = await resolve_queue_concurrency(session)

        assert value == 1
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_finalize_incomplete_jobs_marks_cancelled():
    """Startup cleanup should cancel queued/processing/cancelling jobs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            username="cancel_admin", email="cancel_admin@selenite.local", hashed_password="hashed"
        )
        session.add(user)
        await session.flush()
        jobs = [
            Job(
                id=str(uuid4()),
                user_id=user.id,
                original_filename="queued.wav",
                saved_filename="queued.wav",
                file_path="/tmp/queued.wav",
                file_size=123,
                mime_type="audio/wav",
                status="queued",
                progress_percent=0,
                model_used="medium",
                has_timestamps=True,
                has_speaker_labels=False,
                created_at=datetime.utcnow(),
            ),
            Job(
                id=str(uuid4()),
                user_id=user.id,
                original_filename="processing.wav",
                saved_filename="processing.wav",
                file_path="/tmp/processing.wav",
                file_size=123,
                mime_type="audio/wav",
                status="processing",
                progress_percent=40,
                model_used="medium",
                has_timestamps=True,
                has_speaker_labels=False,
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow(),
            ),
            Job(
                id=str(uuid4()),
                user_id=user.id,
                original_filename="cancelling.wav",
                saved_filename="cancelling.wav",
                file_path="/tmp/cancelling.wav",
                file_size=123,
                mime_type="audio/wav",
                status="cancelling",
                progress_percent=40,
                model_used="medium",
                has_timestamps=True,
                has_speaker_labels=False,
                created_at=datetime.utcnow(),
            ),
            Job(
                id=str(uuid4()),
                user_id=user.id,
                original_filename="pausing.wav",
                saved_filename="pausing.wav",
                file_path="/tmp/pausing.wav",
                file_size=123,
                mime_type="audio/wav",
                status="pausing",
                progress_percent=40,
                model_used="medium",
                has_timestamps=True,
                has_speaker_labels=False,
                created_at=datetime.utcnow(),
            ),
        ]
        session.add_all(jobs)
        await session.commit()

        cleared = await finalize_incomplete_jobs(session)
        assert cleared == 4
        for job in jobs:
            await session.refresh(job)
            if job.original_filename == "pausing.wav":
                assert job.status == "paused"
                assert job.progress_stage == "paused"
            else:
                assert job.status == "cancelled"
                assert job.progress_stage is None
