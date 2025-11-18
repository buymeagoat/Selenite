"""Transcription service for processing audio/video files with Whisper.

This module processes transcription jobs using the WhisperService.
Handles job status updates, progress tracking, and error handling.
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services.whisper_service import whisper_service


async def process_transcription_job(
    job_id: str, db: AsyncSession, *, should_fail: bool = False
) -> None:
    """
    Process a transcription job using Whisper.

    Args:
        job_id: UUID of the job to process
        db: Database session
        should_fail: If True, simulate a failure (for testing)

    Delegates to WhisperService for actual transcription processing.
    """
    if should_fail:
        # Simulate failure for testing
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error_message = "Simulated transcription failure"
            await db.commit()
        return

    # Use real Whisper service for transcription
    await whisper_service.process_job(job_id, db)


def start_transcription_job_async(job_id: str, db: AsyncSession) -> None:
    """
    Start transcription job in background.

    Args:
        job_id: UUID of job to process
        db: Database session

    Note: Prefer using the job_queue service. This legacy
    helper may be removed in a future increment.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(process_transcription_job(job_id, db))
    else:
        loop.run_until_complete(process_transcription_job(job_id, db))
