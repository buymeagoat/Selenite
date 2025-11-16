"""Transcription service for processing audio/video files with Whisper (simulated).

This module simulates transcription stages for Increment 5:
- loading_model -> transcribing -> finalizing -> completed
- updates progress_percent and estimated_time_left
- supports failure simulation for testing

Real Whisper transcription will be implemented in a later increment.
"""

import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


async def process_transcription_job(
    job_id: str, db: AsyncSession, *, should_fail: bool = False
) -> None:
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
    # Initial brief delay
    await asyncio.sleep(0.1)

    # Get job from database
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        return

    try:
        # Move to processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.progress_percent = 10
        job.progress_stage = "loading_model"
        job.estimated_time_left = 3
        await db.commit()

        await asyncio.sleep(0.5)  # Longer delay for test observability

        if should_fail:
            raise RuntimeError("Simulated transcription failure")

        # Transcribing stage
        job.progress_percent = 50
        job.progress_stage = "transcribing"
        job.estimated_time_left = 2
        await db.commit()

        await asyncio.sleep(0.5)

        # Finalizing stage
        job.progress_percent = 85
        job.progress_stage = "finalizing"
        job.estimated_time_left = 1
        await db.commit()

        await asyncio.sleep(0.5)

        # Completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100
        job.progress_stage = None
        job.estimated_time_left = None

        # Simulated metadata
        job.duration = 60.0
        job.language_detected = "en"
        job.speaker_count = 1

        # Optionally set transcript path (placeholder)
        # job.transcript_path = f"./storage/transcripts/{job_id}.txt"

        await db.commit()
    except Exception as exc:
        # Failure handling
        job.status = "failed"
        job.progress_stage = None
        job.estimated_time_left = None
        job.error_message = str(exc)
        await db.commit()


def start_transcription_job_async(job_id: str, db: AsyncSession) -> None:
    """
    Start transcription job in background (stub).

    Args:
        job_id: UUID of job to process
        db: Database session

    Note: In Increment 5, prefer using the job_queue service. This legacy
    helper may be removed in a future increment.
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
