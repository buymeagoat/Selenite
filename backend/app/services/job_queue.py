"""Simple in-memory async job queue with concurrency limit for transcription jobs.

This is a simulated queue suitable for Increment 5 testing.
In later increments, this can be replaced or enhanced.
"""

import asyncio
from datetime import datetime
from typing import Set, Optional

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import get_logger
from app.services.transcription import process_transcription_job
from app.models.job import Job
from app.models.user import User
from app.models.user_settings import UserSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_

# Module-level logger for standalone functions
_logger = get_logger(__name__)


class TranscriptionJobQueue:
    def __init__(self, concurrency: int = 3):
        # Defer queue creation until start() to bind to the current event loop
        self._queue: "asyncio.Queue[tuple[str, bool]] | None" = None
        self._workers: list[asyncio.Task] = []
        self._running_ids: Set[str] = set()
        self._concurrency = concurrency
        self._started = False
        self._slot_lock: asyncio.Semaphore | None = None
        self._logger = get_logger(__name__)

    async def start(self):
        if self._started:
            return
        self._started = True
        # Create a fresh queue bound to this loop
        self._queue = asyncio.Queue()
        self._slot_lock = asyncio.Semaphore(self._concurrency)
        for _ in range(self._concurrency):
            task = asyncio.create_task(self._worker())
            self._workers.append(task)
        self._logger.info("Job queue started with %s workers", self._concurrency)

    async def stop(self):
        # Graceful stop: put sentinel values
        if self._queue is not None:
            for _ in self._workers:
                try:
                    await self._queue.put(("__STOP__", False))
                except RuntimeError as exc:
                    if "Event loop is closed" in str(exc):
                        break
                    raise
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
        # Drop the queue so a new one will be created on next start()
        self._queue = None
        self._slot_lock = None
        self._logger.info("Job queue stopped")

    async def _worker(self):
        while True:
            assert self._queue is not None
            try:
                job_id, should_fail = await self._queue.get()
            except RuntimeError as exc:
                if "Event loop is closed" in str(exc):
                    break
                raise
            if job_id == "__STOP__":  # sentinel
                break
            # Skip if already running (duplicate enqueue)
            if job_id in self._running_ids:
                self._queue.task_done()
                continue
            self._running_ids.add(job_id)
            assert self._slot_lock is not None
            try:
                self._logger.debug("Worker picked job %s (should_fail=%s)", job_id, should_fail)
                async with self._slot_lock:
                    async with AsyncSessionLocal() as db:
                        await process_transcription_job(job_id, db, should_fail=should_fail)
                        await db.commit()  # Ensure changes are committed
            except Exception:
                pass  # Errors logged within process_transcription_job
            finally:
                self._running_ids.discard(job_id)
                self._queue.task_done()
                self._logger.debug("Worker finished job %s", job_id)

    async def enqueue(self, job_id: str, *, should_fail: bool = False) -> None:
        # Avoid duplicate enqueues if already queued or running: check running set only
        if job_id in self._running_ids:
            self._logger.debug("Job %s already running; skipping enqueue", job_id)
            return
        # Ensure workers are started even if startup event didn't run (e.g., app startup)
        if not self._started:
            from os import getenv

            force_start = getenv("FORCE_QUEUE_START") == "1"
            if settings.is_testing and not force_start:
                # In unit tests we let fixtures explicitly start the queue to avoid
                # background work interfering with DB state assertions.
                return
            await self.start()
        assert self._queue is not None
        try:
            await self._queue.put((job_id, should_fail))
            self._logger.info("Queued job %s (should_fail=%s)", job_id, should_fail)
        except RuntimeError as exc:
            if "Event loop is closed" in str(exc):
                return
            raise

    async def set_concurrency(self, new_value: int) -> None:
        """Dynamically adjust worker concurrency.

        Gracefully stops existing workers then restarts with new count.
        Pending jobs remain in queue. Running jobs are allowed to finish.
        """
        if new_value <= 0:
            raise ValueError("Concurrency must be >= 1")
        if new_value == self._concurrency:
            return
        self._logger.info("Changing concurrency from %s to %s", self._concurrency, new_value)
        # In test contexts the event loop may already be closing; be defensive.
        try:
            await self.stop()
        except RuntimeError as e:  # e.g. 'Event loop is closed'
            if "Event loop is closed" in str(e):
                # Mark as stopped without awaiting worker shutdown
                self._workers.clear()
                self._started = False
                self._queue = None
            else:
                raise
        self._concurrency = new_value
        # Restart only if a running loop is available
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_closed():
                await self.start()
        except RuntimeError:
            # No running loop (e.g., during teardown); skip auto-start.
            pass

    def validate_concurrency(self, new_value: int) -> None:
        """Validate a new concurrency value without mutating state."""
        if new_value <= 0:
            raise ValueError("Concurrency must be >= 1")


# Global singleton for app lifetime (no timeout-based stall watchdog).
queue = TranscriptionJobQueue(concurrency=3)


async def resume_queued_jobs(queue_obj: TranscriptionJobQueue) -> int:
    """Re-enqueue any jobs that were left in queued status when the app restarts."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Job.id).where(Job.status == "queued"))
        except Exception as exc:
            # Gracefully handle missing table or schema issues during startup.
            from sqlalchemy.exc import OperationalError

            if isinstance(exc, OperationalError) and "no such table: jobs" in str(exc):
                _logger.warning(
                    "Resume skipped: jobs table missing. Apply migrations then restart."
                )
                return 0
            raise

        job_ids = result.scalars().all()

        for job_id in job_ids:
            await queue_obj.enqueue(str(job_id))

        return len(job_ids)


async def finalize_incomplete_jobs(session: AsyncSession) -> int:
    """Mark lingering queued/processing/cancelling jobs as cancelled (startup cleanup)."""
    result = await session.execute(
        select(Job).where(Job.status.in_(["queued", "processing", "cancelling", "pausing"]))
    )
    jobs = result.scalars().all()
    if not jobs:
        return 0
    now = datetime.utcnow()
    for job in jobs:
        if job.status == "pausing":
            if job.started_at:
                job.processing_seconds = int(job.processing_seconds or 0) + int(
                    (now - job.started_at).total_seconds()
                )
                job.started_at = None
            job.status = "paused"
            job.paused_at = job.paused_at or now
            job.progress_stage = "paused"
            job.estimated_time_left = None
            continue
        if job.started_at:
            job.processing_seconds = int(job.processing_seconds or 0) + int(
                (now - job.started_at).total_seconds()
            )
            job.started_at = None
        job.status = "cancelled"
        job.progress_stage = None
        job.estimated_time_left = None
        job.completed_at = job.completed_at or now
    await session.commit()
    return len(jobs)


async def resolve_queue_concurrency(session: AsyncSession) -> Optional[int]:
    """Determine the desired queue concurrency from admin (or fallback) settings."""
    result = await session.execute(
        select(UserSettings)
        .join(User)
        .where(or_(User.username == "admin", User.id == 1))
        .order_by(UserSettings.updated_at.desc())
        .limit(1)
    )
    settings_row = result.scalars().first()
    if not settings_row:
        result = await session.execute(
            select(UserSettings).order_by(UserSettings.updated_at.desc()).limit(1)
        )
        settings_row = result.scalars().first()
    return settings_row.max_concurrent_jobs if settings_row else None
