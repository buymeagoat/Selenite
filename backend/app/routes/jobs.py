"""Job management routes."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
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
    TagResponse,
)
from app.models.tag import Tag
from app.utils.file_handling import save_uploaded_file, generate_secure_filename
from app.utils.file_validation import validate_media_file
from app.services.job_queue import queue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    model: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    enable_timestamps: bool = Form(default=True),
    enable_speaker_detection: bool = Form(default=True),
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

    # Resolve defaults from user settings if omitted
    # Lazy-load settings; if none exist fallback to global defaults
    # Explicitly load user settings to avoid async lazy-load MissingGreenlet errors
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = settings_result.scalar_one_or_none()
    resolved_model = model or (user_settings.default_model if user_settings else "medium")

    # Create job record in database
    job = Job(
        id=str(job_uuid),
        user_id=current_user.id,
        original_filename=file.filename,
        saved_filename=secure_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        status="queued",
        progress_percent=0,
        model_used=resolved_model,
        has_timestamps=enable_timestamps,
        has_speaker_labels=enable_speaker_detection,
        created_at=datetime.utcnow(),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue job for background processing (Increment 5)
    await queue.enqueue(job.id, should_fail=should_fail)

    return JobCreatedResponse(
        id=job.id,
        original_filename=job.original_filename,
        status=job.status,
        created_at=job.created_at,
    )


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
        date_to: Filter jobs created on or before this date
        tags: Comma-separated tag IDs to filter by
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
    job.status = "cancelled"
    job.progress_stage = None
    job.estimated_time_left = None
    await db.commit()
    await db.refresh(job)
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
        has_timestamps=old_job.has_timestamps,
        has_speaker_labels=old_job.has_speaker_labels,
        created_at=datetime.utcnow(),
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    await queue.enqueue(new_job.id)

    return JobCreatedResponse(
        id=new_job.id,
        original_filename=new_job.original_filename,
        status=new_job.status,
        created_at=new_job.created_at,
    )


@router.post("/{job_id}/tags", response_model=list[TagResponse])
async def assign_tag(
    job_id: UUID,
    payload: TagAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a tag to a job. Creates the tag if name provided and not existing.

    Rules:
    - If tag_id supplied: must exist; name/color ignored.
    - If name supplied: reuse existing (case-insensitive) tag or create new.
    - At least one of (tag_id, name) must be provided.
    """
    result = await db.execute(
        select(Job)
        .where(Job.id == str(job_id), Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not payload.tag_id and not payload.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provide tag_id or name"
        )

    tag: Tag | None = None
    if payload.tag_id:
        tag_res = await db.execute(select(Tag).where(Tag.id == payload.tag_id))
        tag = tag_res.scalar_one_or_none()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    else:
        # Reuse existing by name (case-insensitive)
        tag_res = await db.execute(select(Tag).where(func.lower(Tag.name) == payload.name.lower()))
        tag = tag_res.scalar_one_or_none()
        if not tag:
            tag = Tag(name=payload.name, color=payload.color)
            db.add(tag)
            await db.flush()  # ensure id

    if tag not in job.tags:
        job.tags.append(tag)
        await db.commit()
        await db.refresh(job)

    return [TagResponse.model_validate(t) for t in job.tags]


@router.delete("/{job_id}/tags/{tag_id}", response_model=list[TagResponse])
async def remove_tag(
    job_id: UUID,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a tag association from a job."""
    result = await db.execute(
        select(Job)
        .where(Job.id == str(job_id), Job.user_id == current_user.id)
        .options(selectinload(Job.tags))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    tag = next((t for t in job.tags if t.id == tag_id), None)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not attached to job")
    job.tags.remove(tag)
    await db.commit()
    await db.refresh(job)
    return [TagResponse.model_validate(t) for t in job.tags]


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job and its associated files."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Delete associated files from storage
    import os
    from pathlib import Path

    # Delete media file
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Failed to delete media file {job.file_path}: {e}")

    # Delete transcript file if exists
    transcript_path = Path(settings.transcript_storage_path) / f"{job.id}.txt"
    if transcript_path.exists():
        try:
            transcript_path.unlink()
        except Exception as e:
            print(f"Failed to delete transcript file {transcript_path}: {e}")

    # Delete segments JSON if exists
    segments_path = Path(settings.transcript_storage_path) / f"{job.id}.json"
    if segments_path.exists():
        try:
            segments_path.unlink()
        except Exception as e:
            print(f"Failed to delete segments file {segments_path}: {e}")

    # Delete job from database
    await db.delete(job)
    await db.commit()
