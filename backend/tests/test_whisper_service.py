"""Unit tests for WhisperService behavior."""

from pathlib import Path
from uuid import uuid4
import sys
import types

import pytest

from app.database import engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.job import Job
from app.models import user_settings as _user_settings  # noqa: F401
from app.services import whisper_service as whisper_module
from app.services.whisper_service import WhisperService
from app.config import settings
from app.utils.security import hash_password


@pytest.fixture
async def test_db(tmp_path, monkeypatch):
    """Spin up tables and ensure storage directories use tmp paths."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            id=1,
            username="svc-user",
            email="svc@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add(user)
        await session.commit()

    media_dir = tmp_path / "media"
    transcripts_dir = tmp_path / "transcripts"
    media_dir.mkdir()
    transcripts_dir.mkdir()
    monkeypatch.setattr(settings, "media_storage_path", str(media_dir))
    monkeypatch.setattr(settings, "transcript_storage_path", str(transcripts_dir))

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def create_job(status: str, *, file_path: Path | None = None) -> str:
    """Helper to insert a job row."""
    job_id = str(uuid4())
    async with AsyncSessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=1,
            original_filename="sample.mp3",
            saved_filename="sample.mp3",
            file_path=str(file_path or Path(settings.media_storage_path) / "sample.mp3"),
            file_size=1024,
            mime_type="audio/mpeg",
            status=status,
            progress_percent=0,
            has_timestamps=True,
            has_speaker_labels=False,
        )
        session.add(job)
        await session.commit()
    return job_id


async def get_job(job_id: str) -> Job:
    async with AsyncSessionLocal() as session:
        return await session.get(Job, job_id)


@pytest.mark.anyio
async def test_finalize_cancellation_sets_fields(test_db):
    job_id = await create_job("cancelling")
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        service = WhisperService(model_storage_path=settings.media_storage_path)
        await service._finalize_cancellation(job, session, "test")
        refreshed = await session.get(Job, job_id)
        assert refreshed.status == "cancelled"
        assert refreshed.completed_at is not None
        assert refreshed.progress_stage is None


@pytest.mark.anyio
async def test_abort_if_cancelled_returns_true(test_db):
    job_id = await create_job("cancelling")
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        service = WhisperService(model_storage_path=settings.media_storage_path)
        result = await service._abort_if_cancelled(job, session, "stage")
        assert result is True
        refreshed = await session.get(Job, job_id)
        assert refreshed.status == "cancelled"


@pytest.mark.anyio
async def test_process_job_success(monkeypatch, tmp_path, test_db):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake")
    job_id = await create_job("queued", file_path=audio_path)
    monkeypatch.setattr(
        settings.__class__,
        "is_testing",
        property(lambda self: False),
    )
    service = WhisperService(model_storage_path=settings.media_storage_path)

    async def fake_transcribe(*args, **kwargs):
        return {
            "text": "transcript text",
            "segments": [],
            "duration": 12.0,
            "language": "en",
        }

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_wait_for_processing_slot", noop)
    monkeypatch.setattr(service, "load_model", noop)
    monkeypatch.setattr(service, "transcribe_audio", fake_transcribe)

    async with AsyncSessionLocal() as session:
        await service.process_job(job_id, session)

    job = await get_job(job_id)
    assert job.status == "completed"
    assert job.progress_percent == 100
    assert job.transcript_path
    assert Path(job.transcript_path).exists()


@pytest.mark.anyio
async def test_process_job_failure_sets_error(monkeypatch, tmp_path, test_db):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake")
    job_id = await create_job("queued", file_path=audio_path)
    monkeypatch.setattr(
        settings.__class__,
        "is_testing",
        property(lambda self: False),
    )
    service = WhisperService(model_storage_path=settings.media_storage_path)

    async def failing_transcribe(*args, **kwargs):
        raise RuntimeError("boom")

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_wait_for_processing_slot", noop)
    monkeypatch.setattr(service, "load_model", noop)
    monkeypatch.setattr(service, "transcribe_audio", failing_transcribe)

    async with AsyncSessionLocal() as session:
        await service.process_job(job_id, session)

    job = await get_job(job_id)
    assert job.status == "failed"
    assert job.error_message == "boom"


@pytest.mark.anyio
async def test_process_job_missing_job_noop(test_db):
    service = WhisperService(model_storage_path=settings.media_storage_path)
    async with AsyncSessionLocal() as session:
        await service.process_job("nonexistent", session)


@pytest.mark.anyio
async def test_load_model_missing_file_raises(tmp_path, monkeypatch):
    whisper_module._model_cache.clear()
    fake_whisper = types.SimpleNamespace(load_model=lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)
    service = WhisperService(model_storage_path=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        await service.load_model("base")


@pytest.mark.anyio
async def test_load_model_caches(monkeypatch, tmp_path):
    whisper_module._model_cache.clear()
    model_file = tmp_path / "base.pt"
    model_file.write_text("fake")
    load_calls = []

    def fake_load_model(name, download_root):
        load_calls.append(name)
        return {"name": name}

    class DummyLoop:
        def __init__(self):
            self.calls = 0

        async def run_in_executor(self, executor, func):
            self.calls += 1
            return func()

    dummy_loop = DummyLoop()
    monkeypatch.setattr("asyncio.get_event_loop", lambda: dummy_loop)
    monkeypatch.setitem(sys.modules, "whisper", types.SimpleNamespace(load_model=fake_load_model))

    service = WhisperService(model_storage_path=str(tmp_path))
    first = await service.load_model("base")
    second = await service.load_model("base")

    assert first == second == {"name": "base"}
    assert dummy_loop.calls == 1
    assert load_calls == ["base"]


@pytest.mark.anyio
async def test_transcribe_audio_missing_file(monkeypatch):
    service = WhisperService(model_storage_path=settings.media_storage_path)
    with pytest.raises(FileNotFoundError):
        await service.transcribe_audio("missing.wav", model_name="base")


@pytest.mark.anyio
async def test_transcribe_audio_wraps_exceptions(monkeypatch, tmp_path):
    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"fake")
    service = WhisperService(model_storage_path=settings.media_storage_path)

    class DummyLoop:
        async def run_in_executor(self, executor, func):
            return func()

    class DummyModel:
        def transcribe(self, *args, **kwargs):
            raise ValueError("decode failed")

    async def fake_load_model(name):
        return DummyModel()

    monkeypatch.setattr("asyncio.get_event_loop", lambda: DummyLoop())
    monkeypatch.setattr(service, "load_model", fake_load_model)

    with pytest.raises(RuntimeError):
        await service.transcribe_audio(str(audio_path), model_name="base")


def test_normalize_segments_handles_invalid(tmp_path):
    service = WhisperService(model_storage_path=settings.media_storage_path)
    segments = [
        {"id": 5, "start": "1.5", "end": "2.5", "text": " hello "},
        "bad",
        {"text": None},
    ]
    normalized = service._normalize_segments(segments)
    assert len(normalized) == 1
    assert normalized[0]["text"] == "hello"


def test_normalize_segments_handles_objects():
    service = WhisperService(model_storage_path=settings.media_storage_path)

    class DummySegment:
        def __init__(self, start, end, text, speaker=None):
            self.start = start
            self.end = end
            self.text = text
            self.speaker = speaker

    segments = [
        DummySegment(0.0, 1.5, "First", "Speaker 1"),
        DummySegment(1.5, 3.0, "Second "),
    ]
    normalized = service._normalize_segments(segments)
    assert len(normalized) == 2
    assert normalized[0]["speaker"] == "Speaker 1"
    assert normalized[1]["text"] == "Second"


@pytest.mark.anyio
async def test_wait_for_processing_slot_respects_max_zero(monkeypatch, test_db):
    service = WhisperService(model_storage_path=settings.media_storage_path)
    monkeypatch.setattr(settings, "max_concurrent_jobs", 0)
    async with AsyncSessionLocal() as session:
        await service._wait_for_processing_slot(session)
