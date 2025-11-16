"""Transcription service for processing audio/video files with Whisper.

This is currently a stub implementation that immediately marks jobs as completed.
Real Whisper transcription will be implemented in Build Increment 5.
"""

import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job


async def process_transcription_job(job_id: str, db: AsyncSession) -> None:
    """
    Process a transcription job (stub implementation).

    In this stub version, the job is immediately marked as completed
    without actual transcription. This allows testing the full job
    creation workflow.

    Args:
        job_id: UUID of the job to process
        db: Database session

    Future implementation will:
    1. Load the Whisper model
    2. Process the audio/video file
    3. Update progress in database
    4. Save transcript to storage
    5. Update job with results
    """
    # Simulate brief processing delay
    await asyncio.sleep(0.5)

    # Get job from database
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        return

    # Mark as processing
    job.status = "processing"
    job.started_at = datetime.utcnow()
    job.progress_percent = 10
    job.progress_stage = "loading_model"
    await db.commit()

    # Simulate processing
    await asyncio.sleep(0.5)

    # Update progress
    job.progress_percent = 50
    job.progress_stage = "transcribing"
    await db.commit()

    await asyncio.sleep(0.5)

    # Mark as completed (stub - no actual transcript)
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    job.progress_percent = 100
    job.progress_stage = None
    job.estimated_time_left = None

    # Stub data
    job.duration = 60.0  # Fake 1-minute duration
    job.language_detected = "en"
    job.speaker_count = 1

    # In real implementation, would save transcript file here
    # job.transcript_path = f"./storage/transcripts/{job_id}.txt"

    await db.commit()


def start_transcription_job_async(job_id: str, db: AsyncSession) -> None:
    """
    Start transcription job in background (stub).

    Args:
        job_id: UUID of job to process
        db: Database session

    Note: In Build Increment 5, this will use a proper job queue
    with worker pool. For now, jobs complete immediately.
    """
    # For now, we'll process synchronously in the background
    # Real implementation will use asyncio.create_task or a job queue
    import asyncio

    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Create task in existing loop
        asyncio.create_task(process_transcription_job(job_id, db))
    else:
        # Run in new event loop (for testing)
        loop.run_until_complete(process_transcription_job(job_id, db))
