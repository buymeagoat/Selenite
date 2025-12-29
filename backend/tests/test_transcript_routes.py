"""Tests for transcript retrieval and export endpoints."""

import io
import json
import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.config import settings
from app.models.user import User
from app.models.job import Job
from app.utils.security import create_access_token, hash_password
from app.services.job_queue import queue
from app.routes import transcripts as transcript_routes
from sqlalchemy import select


@pytest.fixture
async def test_db():
    """Create test database and ensure storage dirs."""
    os.makedirs(settings.media_storage_path, exist_ok=True)
    os.makedirs(settings.transcript_storage_path, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test users
        users = [
            User(
                id=1,
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("changeme"),
            ),
            User(
                id=2,
                username="other",
                email="other@example.com",
                hashed_password=hash_password("changeme"),
            ),
        ]
        session.add_all(users)
        await session.commit()

        # Seed minimal ASR registry entry so jobs can be created
        from app.config import BACKEND_ROOT
        from app.schemas.model_registry import ModelSetCreate, ModelWeightCreate
        from app.services.model_registry import ModelRegistryService

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


@pytest.fixture
async def other_auth_headers():
    token = create_access_token(data={"user_id": 2, "username": "other"})
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


async def create_manual_job(job_id: str, user_id: int, status: str):
    async with AsyncSessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=user_id,
            original_filename="manual.mp3",
            saved_filename="manual.mp3",
            file_path="/tmp/manual.mp3",
            file_size=100,
            mime_type="audio/mpeg",
            status=status,
            progress_percent=0,
            has_timestamps=True,
            has_speaker_labels=False,
        )
        session.add(job)
        await session.commit()


async def update_job(job_id: str, **fields) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        for key, value in fields.items():
            setattr(job, key, value)
        await session.commit()


async def create_job_with_transcript(user_id: int, tmp_path, status: str = "completed") -> Job:
    transcript_file = tmp_path / f"{uuid4()}.txt"
    transcript_file.write_text("hello world", encoding="utf-8")
    metadata = transcript_file.with_suffix(".json")
    metadata.write_text(
        json.dumps(
            {
                "text": "hello world metadata",
                "language": "es",
                "duration": 12.5,
                "segments": [
                    {"id": 1, "start": 0.0, "end": 5.0, "text": "hola"},
                    {"id": 2, "start": 5.0, "end": 10.0, "text": "mundo"},
                ],
            }
        ),
        encoding="utf-8",
    )

    async with AsyncSessionLocal() as session:
        job = Job(
            id=str(uuid4()),
            user_id=user_id,
            original_filename="meeting.mp3",
            saved_filename="meeting.mp3",
            file_path="/tmp/meeting.mp3",
            file_size=256,
            mime_type="audio/mpeg",
            status=status,
            progress_percent=100 if status == "completed" else 50,
            transcript_path=str(transcript_file),
            language_detected="en",
            duration=9.0,
            has_timestamps=True,
            has_speaker_labels=False,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


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
            assert body["has_timestamps"] is True
            assert body["has_speaker_labels"] in (True, False)

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
                assert cd.startswith("attachment;") and f"meeting.{fmt}" in cd
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

    async def test_get_transcript_not_completed(self, test_db, auth_headers):
        manual_id = "11111111-1111-1111-1111-111111111111"
        await create_manual_job(manual_id, user_id=1, status="processing")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/transcripts/{manual_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_transcript_missing_job(self, test_db, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/transcripts/00000000-0000-0000-0000-000000000000", headers=auth_headers
            )
        assert resp.status_code == 404

    async def test_export_transcript_requires_ownership(
        self, test_db, auth_headers, other_auth_headers
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"file": ("lecture.mp4", io.BytesIO(b"fake video"), "video/mp4")}
            resp = await client.post("/jobs", files=files, headers=auth_headers)
            job_id = resp.json()["id"]
            await queue.enqueue(job_id)
            await wait_for_status(job_id, "completed", timeout=6.0)
            unauthorized = await client.get(
                f"/transcripts/{job_id}/export",
                params={"format": "txt"},
                headers=other_auth_headers,
            )
            assert unauthorized.status_code == 404

    async def test_transcript_returns_real_text_and_segments(self, test_db, auth_headers, tmp_path):
        manual_id = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
        await create_manual_job(manual_id, user_id=1, status="completed")
        transcript_path = tmp_path / f"{manual_id}.txt"
        transcript_path.write_text("Actual transcript text", encoding="utf-8")
        metadata = {
            "text": "Actual transcript text",
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.5, "text": "Actual"},
                {"id": 1, "start": 2.5, "end": 5.0, "text": "transcript text"},
            ],
            "language": "en",
            "duration": 5.0,
        }
        metadata_path = transcript_path.with_suffix(".json")
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        await update_job(
            manual_id,
            transcript_path=str(transcript_path),
            duration=5.0,
            language_detected="en",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            t_resp = await client.get(f"/transcripts/{manual_id}", headers=auth_headers)
            assert t_resp.status_code == 200
            body = t_resp.json()
            assert body["text"] == "Actual transcript text"
            assert body["segments"][0]["text"] == "Actual"
            assert body["segments"][1]["end"] == 5.0

            export_resp = await client.get(
                f"/transcripts/{manual_id}/export",
                params={"format": "txt"},
                headers=auth_headers,
            )
            assert export_resp.status_code == 200
            assert "Actual transcript text" in export_resp.text


def test_load_transcript_missing_path():
    """_load_transcript_data should raise 404 when no path is stored."""
    job = SimpleNamespace(transcript_path=None, language_detected=None, duration=None)
    with pytest.raises(HTTPException) as exc:
        transcript_routes._load_transcript_data(job)
    assert exc.value.status_code == 404


def test_load_transcript_missing_file(tmp_path):
    """Missing transcript file raises 404 even if path is set."""
    job = SimpleNamespace(
        transcript_path=str(tmp_path / "ghost.txt"), language_detected="en", duration=0.0
    )
    with pytest.raises(HTTPException) as exc:
        transcript_routes._load_transcript_data(job)
    assert exc.value.status_code == 404


def test_load_transcript_falls_back_to_default_path(tmp_path, monkeypatch):
    """Fallback to transcript storage path when job.transcript_path is missing."""
    job_id = "fallback-job"
    fallback_path = tmp_path / f"{job_id}.txt"
    fallback_path.write_text("Fallback text", encoding="utf-8")
    monkeypatch.setattr(settings, "transcript_storage_path", str(tmp_path))
    job = SimpleNamespace(
        id=job_id,
        transcript_path=None,
        language_detected="en",
        duration=12.0,
        has_timestamps=False,
        has_speaker_labels=False,
    )

    text, _, _, _, _, _ = transcript_routes._load_transcript_data(job)

    assert text == "Fallback text"


def test_load_transcript_with_metadata(tmp_path):
    """Metadata file should override language/duration and normalize segments."""
    transcript_file = tmp_path / "sample.txt"
    transcript_file.write_text("", encoding="utf-8")
    metadata = transcript_file.with_suffix(".json")
    metadata.write_text(
        json.dumps(
            {
                "text": "from metadata",
                "language": "fr",
                "duration": 22.5,
                "segments": [
                    {"start": 0, "end": 2.5, "text": "bonjour", "speaker": "Speaker 1"},
                    {"start": 2.5, "end": 5.0, "text": "monde", "speaker": "Speaker 2"},
                ],
            }
        ),
        encoding="utf-8",
    )
    job = SimpleNamespace(
        transcript_path=str(transcript_file),
        language_detected="en",
        duration=10.0,
        has_timestamps=False,
        has_speaker_labels=False,
    )

    text, segments, language, duration, has_timestamps, has_speaker_labels = (
        transcript_routes._load_transcript_data(job)
    )

    assert text == "from metadata"
    assert language == "fr"
    assert duration == 22.5
    assert len(segments) == 2
    assert segments[0]["text"] == "bonjour"
    assert segments[0]["speaker"] == "Speaker 1"


@pytest.mark.asyncio
async def test_get_transcript_requires_completed(test_db, tmp_path):
    """Direct handler call should 404 for non-completed jobs."""
    job = await create_job_with_transcript(user_id=1, tmp_path=tmp_path, status="processing")
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        with pytest.raises(HTTPException):
            await transcript_routes.get_transcript(UUID(job.id), current_user=user, db=session)


@pytest.mark.asyncio
async def test_export_transcript_invalid_format(test_db, tmp_path):
    """Invalid export formats raise HTTP 400."""
    job = await create_job_with_transcript(user_id=1, tmp_path=tmp_path)
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        with pytest.raises(HTTPException):
            await transcript_routes.export_transcript(
                UUID(job.id), format="pdf", current_user=user, db=session
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ["txt", "md", "srt", "vtt", "json", "docx"])
async def test_export_transcript_formats(test_db, tmp_path, fmt, monkeypatch):
    """Ensure each export branch returns a response with expected filename."""
    job = await create_job_with_transcript(user_id=1, tmp_path=tmp_path)
    fake_content = f"{fmt}-content".encode()
    fake_type = f"text/{fmt}"

    def _make_fake():
        return lambda *args, **kwargs: (fake_content, fake_type)

    monkeypatch.setattr(transcript_routes, "export_txt", _make_fake())
    monkeypatch.setattr(transcript_routes, "export_md", _make_fake())
    monkeypatch.setattr(transcript_routes, "export_srt", _make_fake())
    monkeypatch.setattr(transcript_routes, "export_vtt", _make_fake())
    monkeypatch.setattr(transcript_routes, "export_json", _make_fake())
    monkeypatch.setattr(transcript_routes, "export_docx", _make_fake())

    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await transcript_routes.export_transcript(
            UUID(job.id), format=fmt, current_user=user, db=session
        )

    assert response.headers["Content-Disposition"].endswith(f'.{fmt}"')
    assert response.body == fake_content
