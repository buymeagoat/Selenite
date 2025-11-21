"""Unit tests for app.services.transcription module."""

import pytest

from app.database import AsyncSessionLocal, engine, Base
from app.models.job import Job
from app.services import transcription as transcription_service
from app.config import settings


@pytest.fixture(autouse=True)
async def setup_db(tmp_path):
    """Create/drop schema around each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    settings.media_storage_path = str(tmp_path / "media")
    settings.transcript_storage_path = str(tmp_path / "transcripts")

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_job(status="queued") -> str:
    async with AsyncSessionLocal() as session:
        job = Job(
            id="00000000-0000-0000-0000-000000000001",
            user_id=1,
            original_filename="sample.mp3",
            saved_filename="sample.mp3",
            file_path=str(settings.media_storage_path),
            file_size=128,
            mime_type="audio/mpeg",
            status=status,
            has_timestamps=True,
            has_speaker_labels=False,
        )
        session.add(job)
        await session.commit()
    return job.id


@pytest.mark.asyncio
async def test_process_transcription_job_should_fail_creates_error():
    job_id = await _create_job()
    async with AsyncSessionLocal() as session:
        await transcription_service.process_transcription_job(job_id, session, should_fail=True)
        refreshed = await session.get(Job, job_id)
        assert refreshed.status == "failed"
        assert refreshed.error_message == "Simulated transcription failure"


@pytest.mark.asyncio
async def test_process_transcription_job_invokes_whisper(monkeypatch):
    job_id = await _create_job()
    async with AsyncSessionLocal() as session:
        called = {}

        async def fake_process(job_id_arg, db_arg, **_):
            called["job_id"] = job_id_arg
            called["db"] = db_arg

        monkeypatch.setattr(transcription_service.whisper_service, "process_job", fake_process)
        await transcription_service.process_transcription_job(job_id, session)
        assert called["job_id"] == job_id
        assert called["db"] == session


def test_start_transcription_job_async_running_loop(monkeypatch):
    """When loop is running, create_task should be invoked."""
    captured = {}

    class FakeLoop:
        def is_running(self):
            return True

    def fake_create_task(coro):
        captured["called"] = True
        coro.close()

    async def fake_process(job_id, db, **_):
        return None

    monkeypatch.setattr(transcription_service, "process_transcription_job", fake_process)
    monkeypatch.setattr(transcription_service.asyncio, "get_event_loop", lambda: FakeLoop())
    monkeypatch.setattr(transcription_service.asyncio, "create_task", fake_create_task)

    transcription_service.start_transcription_job_async("job-id", None)
    assert captured.get("called") is True


def test_start_transcription_job_async_stopped_loop(monkeypatch):
    """When loop not running, run_until_complete is used."""

    class FakeLoop:
        def __init__(self):
            self.called = False

        def is_running(self):
            return False

        def run_until_complete(self, coro):
            self.called = True
            coro.close()

    fake_loop = FakeLoop()

    async def fake_process(job_id, db, **_):
        return None

    monkeypatch.setattr(transcription_service, "process_transcription_job", fake_process)
    monkeypatch.setattr(transcription_service.asyncio, "get_event_loop", lambda: fake_loop)

    transcription_service.start_transcription_job_async("job-id", None)
    assert fake_loop.called is True
