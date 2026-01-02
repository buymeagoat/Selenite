"""Job management routes."""

from app.schemas.tag import JobTagsResponse, TagBasic

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.models.job import Job
from app.models.tag import job_tags
from app.models.user_settings import UserSettings
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.job import (
    JobCreatedResponse,
    JobListResponse,
    JobListItem,
    JobResponse,
    JobStatusResponse,
    TagAssignRequest,
    JobRenameRequest,
)
from app.models.tag import Tag
from app.utils.file_handling import (
    save_uploaded_file,
    generate_secure_filename,
    build_job_filename,
    resolve_unique_media_path,
)
from app.utils.file_validation import validate_media_file
from app.services.job_queue import queue
from app.services.capabilities import ModelResolutionError, resolve_job_preferences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    job_name: Optional[str] = Form(default=None, alias="job_name"),
    provider: Optional[str] = Form(default=None, alias="provider"),
    model: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    enable_timestamps: bool = Form(default=True),
    enable_speaker_detection: bool = Form(default=True),
    diarizer: Optional[str] = Form(default=None),
    speaker_count: Optional[int] = Form(default=None),
    should_fail: bool = Query(False, alias="fail"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new transcription job with file upload.

    Args:
        file: Audio or video file to transcribe
        model: Whisper model to use (tiny, base, small, medium, large)
        language: Language code or "auto" for auto-detection
        enable_timestamps: Whether to include timestamps in transcript
        enable_speaker_detection: Whether to detect and label speakers
        current_user: Authenticated user from dependency
        db: Database session

    Returns:
        JobCreatedResponse with job ID and initial status

    Raises:
        HTTPException: 400 if file format invalid, 413 if file too large
    """
    # Validate uploaded file for security and format
    validated_mime, validated_size = await validate_media_file(file)

    # Save file to storage
    file_path, file_size, mime_type = await save_uploaded_file(file, settings.media_storage_path)

    # Generate secure filename and get UUID
    secure_filename, job_uuid = generate_secure_filename(file.filename)

    # Normalize job name (defaults to the uploaded filename)
    requested_name = job_name or file.filename
    extension = Path(file.filename).suffix or Path(file_path).suffix
    try:
        normalized_name = build_job_filename(requested_name, extension)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if len(normalized_name) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is too long",
        )

    target_path = resolve_unique_media_path(normalized_name, settings.media_storage_path, file_path)
    current_path = Path(file_path)
    if not current_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uploaded file missing from storage",
        )
    if current_path.resolve() != target_path.resolve():
        current_path.rename(target_path)
        file_path = str(target_path)
    secure_filename = target_path.name

    # Validate speaker_count if provided
    if speaker_count is not None:
        if speaker_count < 2 or speaker_count > 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="speaker_count must be between 2 and 8, or omitted for auto-detect",
            )

    # Resolve defaults from user settings if omitted
    # Lazy-load settings; if none exist fallback to global defaults
    # Explicitly load user settings to avoid async lazy-load MissingGreenlet errors
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = settings_result.scalar_one_or_none()

    try:
        preference = resolve_job_preferences(
            requested_model=model,
            requested_provider=provider,
            requested_diarizer=diarizer,
            requested_diarization=enable_speaker_detection,
            user_settings=user_settings,
        )
    except ModelResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    resolved_model = preference["model"]
    diarizer_used = preference["diarizer"]
    diarizer_provider_used = preference.get("diarizer_provider")
    diarization_active = preference["diarization_enabled"]
    for note in preference["notes"]:
        logger.warning("Job %s preference adjustment: %s", job_uuid, note)

    if resolved_model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ASR models available; contact admin to register a model.",
        )

    # Create job record in database
    job = Job(
        id=str(job_uuid),
        user_id=current_user.id,
        original_filename=normalized_name,
        saved_filename=secure_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        status="queued",
        progress_percent=0,
        model_used=resolved_model,
        asr_provider_used=preference.get("provider"),
        has_timestamps=enable_timestamps,
        has_speaker_labels=diarization_active,
        diarizer_used=diarizer_used,
        diarizer_provider_used=diarizer_provider_used,
        speaker_count=speaker_count,
        created_at=datetime.utcnow(),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue job for background processing (Increment 5)
    await queue.enqueue(str(job.id), should_fail=should_fail)

    return JobCreatedResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tag IDs to filter (ANY match)"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all jobs with optional filtering and pagination.

    Args:
        status_filter: Filter by job status (queued, processing, completed, failed)
        date_from: Filter jobs created on or after this date
        search: Search term for filename or transcript content
        limit: Maximum number of results to return
        offset: Number of results to skip for pagination
        current_user: Authenticated user from dependency
        db: Database session

    Returns:
        JobListResponse with total count and paginated list of jobs
    """
    # Build base query for user's jobs
    query = select(Job).where(Job.user_id == current_user.id).options(selectinload(Job.tags))

    # Apply status filter
    if status_filter:
        query = query.where(Job.status == status_filter)

    # Apply date range filters
    if date_from:
        query = query.where(Job.created_at >= date_from)
    if date_to:
        query = query.where(Job.created_at <= date_to)

    # Apply search filter (filename only for now, transcript search in later increment)
    if search:
        query = query.where(Job.original_filename.ilike(f"%{search}%"))

    # Tag filtering (ANY match of provided tag IDs)
    if tags:
        try:
            tag_ids = [int(t.strip()) for t in tags.split(",") if t.strip()]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tag id")
        if tag_ids:
            subq = select(job_tags.c.job_id).where(job_tags.c.tag_id.in_(tag_ids))
            query = query.where(Job.id.in_(subq))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply ordering (newest first)
    query = query.order_by(Job.created_at.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    # Convert to response models
    items = [JobListItem.model_validate(job) for job in jobs]

    return JobListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/stream")
async def stream_jobs(current_user: User = Depends(get_current_user)):
    async def event_generator():
        last_payload = None
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Job)
                        .where(Job.user_id == current_user.id)
                        .options(selectinload(Job.tags))
                        .order_by(Job.created_at.desc())
                    )
                    jobs = result.scalars().all()

                items = [JobListItem.model_validate(job).model_dump(mode="json") for job in jobs]
                payload = json.dumps({"items": items})
                if payload != last_payload:
                    yield f"event: jobs\ndata: {payload}\n\n"
                    last_payload = payload
                else:
                    yield "event: heartbeat\ndata: {}\n\n"
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Job stream error: %s", exc)
                yield f"event: error\ndata: {json.dumps({'detail': 'stream_error'})}\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific job.

    Args:
        job_id: UUID of the job to retrieve
        current_user: Authenticated user from dependency
        db: Database session

    Returns:
        JobResponse with complete job information

    Raises:
        HTTPException: 404 if job not found
    """
    # Query for the job
    query = (
        select(Job)
        .where(Job.id == str(job_id), Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobResponse.model_validate(job)


@router.patch("/{job_id}/rename", response_model=JobResponse)
async def rename_job(
    job_id: UUID,
    payload: JobRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a job and its underlying media file."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in {"processing", "cancelling"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rename an active job",
        )
    if not job.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )

    extension = Path(job.original_filename).suffix or Path(job.file_path).suffix
    try:
        normalized_name = build_job_filename(payload.name, extension)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if len(normalized_name) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is too long",
        )

    current_path = Path(job.file_path)
    if not current_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )

    target_path = resolve_unique_media_path(
        normalized_name, settings.media_storage_path, job.file_path
    )
    if current_path.resolve() != target_path.resolve():
        current_path.rename(target_path)
        job.file_path = str(target_path)
        job.saved_filename = target_path.name

    job.original_filename = normalized_name
    await db.commit()
    result = await db.execute(
        select(Job).where(Job.id == str(job_id)).options(selectinload(Job.tags))
    )
    job = result.scalar_one()
    return JobResponse.model_validate(job)


@router.get("/{job_id}/media")
async def download_media(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the original media file for a job."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    filename = Path(job.original_filename).name
    media_type = job.mime_type or "application/octet-stream"
    return FileResponse(
        path=job.file_path,
        media_type=media_type,
        filename=filename,
        headers={"Access-Control-Expose-Headers": "Content-Disposition"},
    )


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a queued or processing job."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not cancellable in its current state",
        )
    if job.status in {"processing", "pausing"}:
        job.status = "cancelling"
        job.progress_stage = "cancelling"
    elif job.status == "paused":
        job.status = "cancelled"
        job.progress_stage = None
        job.completed_at = datetime.utcnow()
    else:
        job.status = "cancelled"
        job.progress_stage = None
        job.completed_at = datetime.utcnow()
    job.estimated_time_left = None
    await db.commit()
    await db.refresh(job)
    return JobStatusResponse.model_validate(job)


@router.post("/{job_id}/pause", response_model=JobStatusResponse)
async def pause_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause a queued or processing job (checkpointed after current chunk)."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not pausable in its current state",
        )
    if job.status == "processing" and job.progress_stage == "diarizing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be paused during diarization",
        )
    if job.status == "paused":
        return JobStatusResponse.model_validate(job)

    now = datetime.utcnow()
    job.pause_requested_at = now
    if job.status == "queued":
        job.status = "paused"
        job.paused_at = now
        job.progress_stage = "paused"
        job.estimated_time_left = None
    elif job.status == "processing":
        job.status = "pausing"
        job.progress_stage = "pausing"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not pausable in its current state",
        )
    await db.commit()
    await db.refresh(job)
    return JobStatusResponse.model_validate(job)


@router.post("/{job_id}/resume", response_model=JobStatusResponse)
async def resume_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused job (re-queues with checkpoint if available)."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not paused",
        )

    job.status = "queued"
    job.progress_stage = None
    job.resume_count = int(job.resume_count or 0) + 1
    await db.commit()
    await db.refresh(job)
    await queue.enqueue(str(job.id))
    logger.info("Job %s resume requested (resume_count=%s)", job.id, job.resume_count)
    return JobStatusResponse.model_validate(job)


@router.post(
    "/{job_id}/restart",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def restart_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restart a completed, failed, or cancelled job by creating a new job record."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    old_job = result.scalar_one_or_none()
    if not old_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if old_job.status in {"processing", "queued"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot restart an active job",
        )

    new_id = uuid4()
    new_job = Job(
        id=str(new_id),
        user_id=current_user.id,
        original_filename=old_job.original_filename,
        saved_filename=old_job.saved_filename,
        file_path=old_job.file_path,
        file_size=old_job.file_size,
        mime_type=old_job.mime_type,
        status="queued",
        progress_percent=0,
        model_used=old_job.model_used,
        asr_provider_used=old_job.asr_provider_used,
        has_timestamps=old_job.has_timestamps,
        has_speaker_labels=old_job.has_speaker_labels,
        diarizer_used=old_job.diarizer_used,
        diarizer_provider_used=old_job.diarizer_provider_used,
        speaker_count=old_job.speaker_count,
        created_at=datetime.utcnow(),
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    await queue.enqueue(str(new_job.id))

    return JobCreatedResponse.model_validate(new_job)


@router.post("/{job_id}/tags", response_model=JobTagsResponse)
async def assign_tag(
    job_id: str,
    assignment: TagAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign tags to a job: bulk assignment only (tag_ids required)."""
    # Validate tag_ids: must be present and a list of integers (can be empty)
    tag_ids = assignment.tag_ids if assignment.tag_ids is not None else []
    if not isinstance(tag_ids, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="tag_ids must be a list"
        )
    if not all(isinstance(tid, int) for tid in tag_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tag_ids must be a list of integers",
        )

    # Get the job
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not tag_ids:
        job.tags.clear()
        await db.commit()
        return JobTagsResponse(job_id=str(job.id), tags=[])

    # Get the tags
    stmt = select(Tag).where(Tag.id.in_(tag_ids))
    result = await db.execute(stmt)
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or more tags not found"
        )

    # Assign tags (idempotent: clear then add)
    job.tags.clear()
    for tag in tags:
        job.tags.append(tag)
    await db.commit()

    return JobTagsResponse(
        job_id=str(job.id),
        tags=[TagBasic.model_validate(tag) for tag in tags],
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a job and its associated files.

    Args:
        job_id: UUID of the job to delete
        current_user: Authenticated user from dependency
        db: Database session

    Raises:
        HTTPException: 404 if job not found, 400 if job is currently processing
    """
    from pathlib import Path
    import os

    # Get the job
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Prevent deletion of actively processing jobs
    if job.status in {"queued", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a job that is currently queued or processing. Cancel it first.",
        )

    # Delete associated files
    files_to_delete = set()
    backend_dir = Path(__file__).parent.parent.parent

    def resolve_path(p: Path) -> Path:
        return p if p.is_absolute() else (backend_dir / p).resolve()

    # Media file from stored path
    if job.file_path:
        files_to_delete.add(resolve_path(Path(job.file_path)))
    # Media file by saved_filename under storage root (in case file_path missing)
    if job.saved_filename:
        files_to_delete.add(Path(settings.media_storage_path) / job.saved_filename)

    # Transcript file from stored path
    if job.transcript_path:
        tp = resolve_path(Path(job.transcript_path))
        files_to_delete.add(tp)
        files_to_delete.add(tp.with_suffix(".json"))

    # Also clear any transcript artifacts matching job.id.* in transcript storage
    transcript_root = Path(settings.transcript_storage_path)
    files_to_delete.add(transcript_root / f"{job.id}.txt")
    files_to_delete.add((transcript_root / f"{job.id}.txt").with_suffix(".json"))
    for ext in [".md", ".srt", ".vtt", ".json", ".docx"]:
        files_to_delete.add(transcript_root / f"{job.id}{ext}")

    # Delete files (silently ignore missing files)
    for file_path in files_to_delete:
        try:
            fp = resolve_path(file_path)
            if fp.exists() and fp.is_file():
                os.remove(fp)
        except Exception:
            # Log but don't fail deletion if file removal fails
            pass

    # Delete job from database
    await db.delete(job)
    await db.commit()

    return None
