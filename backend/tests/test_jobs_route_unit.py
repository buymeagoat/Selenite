"""Additional unit-level coverage for app.routes.jobs edge cases."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, Base, engine
from app.models.job import Job
from app.models.tag import Tag
from app.models.user import User
from app.models.user_settings import UserSettings
from app.routes.jobs import (
    assign_tag,
    cancel_job,
    delete_job,
    get_job,
    list_jobs,
    restart_job,
)
from app.schemas.job import TagAssignRequest
from app.utils.security import hash_password
from app.config import settings


@pytest.fixture
async def session_with_user():
    """Provide a fresh DB session seeded with a default user + settings."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSessionLocal()
    try:
        user = User(
            username="admin",
            email="admin@selenite.local",
            hashed_password=hash_password("changeme"),
        )
        session.add(user)
        await session.flush()
        session.add(UserSettings(user_id=user.id, default_model="medium"))
        await session.commit()
        await session.refresh(user)
        yield session, user
    finally:
        await session.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


async def _create_job(
    session,
    user_id: int,
    *,
    status: str = "queued",
    created_at: datetime | None = None,
    original_filename: str = "clip.mp3",
    file_path: str | None = None,
    transcript_path: str | None = None,
    progress_stage: str | None = None,
) -> Job:
    """Persist a job helper."""
    job = Job(
        id=str(uuid4()),
        user_id=user_id,
        original_filename=original_filename,
        saved_filename="clip.mp3",
        file_path=file_path or str(Path("storage") / "media" / "clip.mp3"),
        file_size=1024,
        mime_type="audio/mpeg",
        status=status,
        progress_percent=5,
        progress_stage=progress_stage,
        model_used="medium",
        has_timestamps=True,
        has_speaker_labels=True,
        created_at=created_at or datetime.utcnow(),
        transcript_path=transcript_path,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _create_tag(session, tag_id: int, name: str = "Tag") -> Tag:
    tag = Tag(id=tag_id, name=name, color="#FF00FF")
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def _attach_tag(session, job_id: str, tag: Tag) -> None:
    result = await session.execute(
        select(Job).options(selectinload(Job.tags)).where(Job.id == job_id)
    )
    job = result.scalar_one()
    job.tags.append(tag)
    await session.commit()


@pytest.mark.asyncio
async def test_list_jobs_filters_and_invalid_tags(session_with_user):
    session, user = session_with_user
    now = datetime.utcnow()
    recent_tag = await _create_tag(session, 1, "Finance")
    older_tag = await _create_tag(session, 2, "Ops")

    keep = await _create_job(
        session,
        user.id,
        status="completed",
        created_at=now - timedelta(hours=1),
        original_filename="finance_report.mp3",
    )
    await _attach_tag(session, keep.id, recent_tag)

    old = await _create_job(
        session,
        user.id,
        status="completed",
        created_at=now - timedelta(days=3),
        original_filename="ops_notes.mp3",
    )
    await _attach_tag(session, old.id, older_tag)

    await _create_job(
        session,
        user.id,
        status="queued",
        created_at=now,
        original_filename="finance_briefing.mp3",
    )
    await session.commit()

    response = await list_jobs(
        status_filter="completed",
        date_from=now - timedelta(days=1),
        date_to=now,
        tags="1",
        search="report",
        limit=5,
        offset=0,
        current_user=user,
        db=session,
    )

    assert response.total == 1
    assert str(response.items[0].id) == keep.id

    with pytest.raises(HTTPException) as exc:
        await list_jobs(tags="invalid", current_user=user, db=session)
    assert exc.value.status_code == 400
    assert "Invalid tag id" in exc.value.detail


@pytest.mark.asyncio
async def test_get_job_and_cancel_states(session_with_user):
    session, user = session_with_user
    queued = await _create_job(session, user.id, status="queued")
    processing = await _create_job(session, user.id, status="processing")

    with pytest.raises(HTTPException) as exc:
        await get_job(UUID(str(uuid4())), current_user=user, db=session)
    assert exc.value.status_code == 404

    cancelled = await cancel_job(UUID(queued.id), current_user=user, db=session)
    assert cancelled.status == "cancelled"

    cancelling = await cancel_job(UUID(processing.id), current_user=user, db=session)
    assert cancelling.status == "cancelling"
    assert cancelling.progress_stage == "cancelling"

    completed = await _create_job(session, user.id, status="completed")
    with pytest.raises(HTTPException) as exc:
        await cancel_job(UUID(completed.id), current_user=user, db=session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_restart_job_paths(session_with_user):
    session, user = session_with_user
    finished = await _create_job(
        session,
        user.id,
        status="completed",
        file_path=str(Path("storage") / "media" / "done.mp3"),
    )
    active = await _create_job(session, user.id, status="processing")

    with patch("app.routes.jobs.queue.enqueue", new=AsyncMock()) as mock_enqueue:
        restarted = await restart_job(UUID(finished.id), current_user=user, db=session)
    assert restarted.status == "queued"
    assert restarted.id != finished.id
    mock_enqueue.assert_awaited_once()

    with pytest.raises(HTTPException) as exc:
        await restart_job(UUID(active.id), current_user=user, db=session)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        await restart_job(UUID(str(uuid4())), current_user=user, db=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_assign_tag_variants(session_with_user):
    session, user = session_with_user
    job = await _create_job(session, user.id, status="completed")
    tag = await _create_tag(session, 10, "Legal")

    response = await assign_tag(
        job_id=job.id,
        assignment=TagAssignRequest(tag_ids=[]),
        current_user=user,
        db=session,
    )
    assert response.tags == []

    with pytest.raises(HTTPException) as exc:
        await assign_tag(
            job_id=job.id,
            assignment=TagAssignRequest(tag_ids=[tag.id, 999]),
            current_user=user,
            db=session,
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await assign_tag(
            job_id=job.id,
            assignment=SimpleNamespace(tag_ids="bad"),
            current_user=user,
            db=session,
        )
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        await assign_tag(
            job_id=job.id,
            assignment=SimpleNamespace(tag_ids=[tag.id, "oops"]),
            current_user=user,
            db=session,
        )
    assert exc.value.status_code == 422

    missing_job = str(uuid4())
    with pytest.raises(HTTPException) as exc:
        await assign_tag(
            job_id=missing_job,
            assignment=TagAssignRequest(tag_ids=[tag.id]),
            current_user=user,
            db=session,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_paths(session_with_user, tmp_path, monkeypatch):
    session, user = session_with_user
    target_media = tmp_path / "sample.mp3"
    target_media.write_bytes(b"bytes")
    transcript_file = tmp_path / "sample.txt"
    transcript_file.write_text("text", encoding="utf-8")
    default_transcripts = tmp_path / "transcripts"
    default_transcripts.mkdir()
    monkeypatch.setattr(settings, "transcript_storage_path", str(default_transcripts))

    job = await _create_job(
        session,
        user.id,
        status="completed",
        file_path=str(target_media),
        transcript_path=str(transcript_file),
    )
    default_copy = default_transcripts / f"{job.id}.txt"
    default_copy.write_text("cached", encoding="utf-8")

    await delete_job(UUID(job.id), current_user=user, db=session)

    assert not target_media.exists()
    assert not transcript_file.exists()
    assert not default_copy.exists()
    remaining = await session.execute(select(Job).where(Job.id == job.id))
    assert remaining.scalar_one_or_none() is None

    with pytest.raises(HTTPException) as exc:
        await delete_job(UUID(job.id), current_user=user, db=session)
    assert exc.value.status_code == 404

    queued = await _create_job(session, user.id, status="queued")
    with pytest.raises(HTTPException) as exc:
        await delete_job(UUID(queued.id), current_user=user, db=session)
    assert exc.value.status_code == 400
