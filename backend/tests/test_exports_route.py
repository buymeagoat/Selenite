"""Tests for transcript export route."""

import json
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException

from app.main import app
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.job import Job
from app.utils.security import hash_password, create_access_token
from app.routes.exports import export_transcript


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
    assert response.status_code == 404


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


@pytest.mark.anyio
async def test_export_falls_back_to_default_transcript_path(
    tmp_path, test_db, auth_headers_user1, monkeypatch
):
    job_id = "job-fallback"
    fallback_path = tmp_path / f"{job_id}.txt"
    fallback_path.write_text("Fallback transcript", encoding="utf-8")
    monkeypatch.setattr(settings, "transcript_storage_path", str(tmp_path))

    job = await _create_job(
        job_id=job_id,
        user_id=1,
        status="completed",
        transcript_path=None,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export?format=txt", headers=auth_headers_user1)

    assert response.status_code == 200
    assert response.text == "Fallback transcript"


@pytest.mark.anyio
async def test_export_md_loads_segments(monkeypatch, tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "segments.txt"
    transcript.write_text("Segmented text", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    payload = {"segments": [{"start": 0.0, "end": 1.0, "text": "piece"}]}
    segments_file.write_text(json.dumps(payload), encoding="utf-8")

    captured = {}

    def fake_export_md(job, transcript_text, segments):
        captured["job"] = job
        captured["text"] = transcript_text
        captured["segments"] = segments
        return b"# markdown"

    monkeypatch.setattr("app.routes.exports.export_service.export_md", fake_export_md)

    job = await _create_job(
        job_id="job-md",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export?format=md", headers=auth_headers_user1)

    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith('.md"')
    assert captured["segments"] == payload["segments"]


@pytest.mark.anyio
async def test_export_docx_handles_missing_segments(
    monkeypatch, tmp_path, test_db, auth_headers_user1
):
    transcript = tmp_path / "docx.txt"
    transcript.write_text("Doc body", encoding="utf-8")

    called = {}

    def fake_export_docx(job, transcript_text, segments):
        called["text"] = transcript_text
        called["segments"] = segments
        return b"DOCX"

    monkeypatch.setattr("app.routes.exports.export_service.export_docx", fake_export_docx)

    job = await _create_job(
        job_id="job-docx",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/jobs/{job.id}/export?format=docx", headers=auth_headers_user1
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert called["text"] == "Doc body"
    assert called["segments"] == []


@pytest.mark.anyio
async def test_export_json_returns_metadata(tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "json.txt"
    transcript.write_text("Full text", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text(
        json.dumps(
            {
                "segments": [{"text": "Full text"}],
                "language": "en",
                "duration": 12.5,
                "model": "medium",
                "speaker_count": 2,
            }
        ),
        encoding="utf-8",
    )

    job = await _create_job(
        job_id="job-json",
        user_id=1,
        status="completed",
        transcript_path=transcript,
        original_filename="call.wav",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/jobs/{job.id}/export?format=json", headers=auth_headers_user1
        )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-json"
    assert data["text"] == "Full text"
    assert data["filename"] == "call.wav"
    assert data["segments"][0]["text"] == "Full text"
    # Metadata persisted on the job record should surface in JSON export
    assert data["language"] is None or data["language"] == "en"
    assert data["duration"] is None or data["duration"] == 12.5


@pytest.mark.anyio
async def test_export_srt_ignores_invalid_segment_json(
    monkeypatch, tmp_path, test_db, auth_headers_user1
):
    transcript = tmp_path / "broken.txt"
    transcript.write_text("Broken text", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text("{not-json", encoding="utf-8")

    captured_segments = {}

    def fake_export_srt(job, segments):
        captured_segments["segments"] = segments
        return b"SRT"

    monkeypatch.setattr("app.routes.exports.export_service.export_srt", fake_export_srt)

    job = await _create_job(
        job_id="job-srt",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export?format=srt", headers=auth_headers_user1)

    assert response.status_code == 200
    assert captured_segments["segments"] == []


@pytest.mark.anyio
async def test_export_docx_dependency_error(monkeypatch, tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "docx_missing_dep.txt"
    transcript.write_text("Doc body", encoding="utf-8")
    job = await _create_job(
        job_id="job-docx-dep",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    def fake_docx(*args, **kwargs):
        raise ImportError("python-docx")

    monkeypatch.setattr("app.routes.exports.export_service.export_docx", fake_docx)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/jobs/{job.id}/export?format=docx", headers=auth_headers_user1
        )

    assert response.status_code == 500
    assert "requires additional dependencies" in response.json()["detail"]


@pytest.mark.anyio
async def test_export_generic_failure(monkeypatch, tmp_path, test_db, auth_headers_user1):
    transcript = tmp_path / "generic.txt"
    transcript.write_text("Generic content", encoding="utf-8")
    job = await _create_job(
        job_id="job-generic-fail",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    def fake_txt(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routes.exports.export_service.export_txt", fake_txt)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/jobs/{job.id}/export?format=txt", headers=auth_headers_user1)

    assert response.status_code == 500
    assert "Failed to export transcript" in response.json()["detail"]


@pytest.mark.anyio
async def test_export_vtt_direct_success(tmp_path, test_db):
    transcript = tmp_path / "direct.txt"
    transcript.write_text("Direct transcript", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text(
        json.dumps({"segments": [{"start": 0.0, "end": 1.2, "text": "Hello"}]}), encoding="utf-8"
    )
    job = await _create_job(
        job_id="job-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
        original_filename="direct.mp3",
    )
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await export_transcript(job.id, "vtt", current_user=user, db=session)
    assert response.media_type == "text/vtt"
    assert response.headers["content-disposition"].endswith('.vtt"')
    assert b"WEBVTT" in response.body


@pytest.mark.anyio
async def test_export_transcript_unauthorized_direct(tmp_path, test_db):
    transcript = tmp_path / "unauthorized.txt"
    transcript.write_text("secret", encoding="utf-8")
    await _create_job(
        job_id="job-unauth-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )
    async with AsyncSessionLocal() as session:
        user2 = await session.get(User, 2)
        with pytest.raises(HTTPException) as exc:
            await export_transcript(
                "job-unauth-direct", "txt", current_user=user2, db=session  # type: ignore[arg-type]
            )
        assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_export_transcript_not_completed_direct(tmp_path, test_db):
    transcript = tmp_path / "pending.txt"
    transcript.write_text("pending", encoding="utf-8")
    await _create_job(
        job_id="job-not-completed",
        user_id=1,
        status="processing",
        transcript_path=transcript,
    )
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        with pytest.raises(HTTPException) as exc:
            await export_transcript("job-not-completed", "txt", current_user=user, db=session)
        assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_export_transcript_missing_file_direct(test_db):
    await _create_job(
        job_id="job-missing-file",
        user_id=1,
        status="completed",
        transcript_path=None,
    )
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        with pytest.raises(HTTPException) as exc:
            await export_transcript("job-missing-file", "txt", current_user=user, db=session)
        assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_export_json_direct(tmp_path, test_db):
    transcript = tmp_path / "json_direct.txt"
    transcript.write_text("json body", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text(json.dumps({"segments": [{"text": "json body"}]}), encoding="utf-8")
    await _create_job(
        job_id="job-json-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )
    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await export_transcript("job-json-direct", "json", current_user=user, db=session)
    assert response.media_type == "application/json"
    assert '"text": "json body"' in response.body.decode("utf-8")


@pytest.mark.anyio
async def test_export_docx_direct(monkeypatch, tmp_path, test_db):
    transcript = tmp_path / "docx_direct.txt"
    transcript.write_text("docx body", encoding="utf-8")
    await _create_job(
        job_id="job-docx-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    def fake_docx(*args, **kwargs):
        return b"DOCX"

    monkeypatch.setattr("app.routes.exports.export_service.export_docx", fake_docx)

    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await export_transcript("job-docx-direct", "docx", current_user=user, db=session)
    assert response.media_type.startswith("application/vnd.openxmlformats")
    assert response.headers["content-disposition"].endswith('.docx"')


@pytest.mark.anyio
async def test_export_md_direct(monkeypatch, tmp_path, test_db):
    transcript = tmp_path / "md_direct.txt"
    transcript.write_text("md body", encoding="utf-8")
    await _create_job(
        job_id="job-md-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    def fake_md(job, text, segments):
        return b"# Markdown"

    monkeypatch.setattr("app.routes.exports.export_service.export_md", fake_md)

    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await export_transcript("job-md-direct", "md", current_user=user, db=session)
    assert response.media_type == "text/markdown"


@pytest.mark.anyio
async def test_export_srt_direct(monkeypatch, tmp_path, test_db):
    transcript = tmp_path / "srt_direct.txt"
    transcript.write_text("srt body", encoding="utf-8")
    segments_file = transcript.with_suffix(".json")
    segments_file.write_text(json.dumps({"segments": [{"text": "line"}]}), encoding="utf-8")
    await _create_job(
        job_id="job-srt-direct",
        user_id=1,
        status="completed",
        transcript_path=transcript,
    )

    def fake_srt(job, segments):
        return b"1\n00:00:00,000 --> 00:00:01,000\nline"

    monkeypatch.setattr("app.routes.exports.export_service.export_srt", fake_srt)

    async with AsyncSessionLocal() as session:
        user = await session.get(User, 1)
        response = await export_transcript("job-srt-direct", "srt", current_user=user, db=session)
    assert response.media_type == "text/plain"
