"""Job management routes."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.job import JobCreatedResponse, JobListResponse, JobListItem, JobResponse
from app.utils.file_handling import save_uploaded_file, generate_secure_filename
from app.services.job_queue import queue

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    model: str = Form(default="medium"),
    language: str = Form(default="auto"),
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
    # Save file to storage
    file_path, file_size, mime_type = await save_uploaded_file(file, settings.media_storage_path)

    # Generate secure filename and get UUID
    secure_filename, job_uuid = generate_secure_filename(file.filename)

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
        model_used=model,
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
    tags: Optional[str] = Query(None),
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

    # TODO: Tag filtering will be implemented when tag relationships are added

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
