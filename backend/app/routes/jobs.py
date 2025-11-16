"""Job management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.job import JobCreatedResponse
from app.utils.file_handling import save_uploaded_file, generate_secure_filename

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    model: str = Form(default="medium"),
    language: str = Form(default="auto"),
    enable_timestamps: bool = Form(default=True),
    enable_speaker_detection: bool = Form(default=True),
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

    # In Build Increment 5, we'll actually queue the transcription job
    # For now, it just stays in "queued" status

    return JobCreatedResponse(
        id=job.id,
        original_filename=job.original_filename,
        status=job.status,
        created_at=job.created_at,
    )
