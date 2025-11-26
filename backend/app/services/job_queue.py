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
from sqlalchemy import select


class TranscriptionJobQueue:
    def __init__(self, concurrency: int = 3, *, enable_watchdog: bool = True):
        # Defer queue creation until start() to bind to the current event loop
        self._queue: "asyncio.Queue[tuple[str, bool]] | None" = None
        self._workers: list[asyncio.Task] = []
        self._running_ids: Set[str] = set()
        self._concurrency = concurrency
        self._started = False
        self._slot_lock: asyncio.Semaphore | None = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._enable_watchdog = enable_watchdog
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
        if self._enable_watchdog:
            self._watchdog_task = asyncio.create_task(self._watchdog())

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
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except Exception:
                pass
            self._watchdog_task = None
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

    async def _watchdog(self) -> None:
        """Fail processing jobs that run far beyond their estimated time."""
        interval = max(1.0, float(settings.stall_check_interval_seconds))
        try:
            while self._started:
                await asyncio.sleep(interval)
                try:
                    now = datetime.utcnow()
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Job).where(
                                Job.status == "processing", Job.started_at.isnot(None)
                            )
                        )
                        jobs = result.scalars().all()
                        changed = False
                        for job in jobs:
                            est_total = (
                                job.estimated_total_seconds
                                or settings.default_estimated_duration_seconds
                            )
                            max_allowed = max(
                                int(est_total * settings.stall_timeout_multiplier),
                                int(settings.stall_timeout_min_seconds),
                            )
                            elapsed = (now - job.started_at).total_seconds()
                            if elapsed > max_allowed:
                                job.status = "failed"
                                job.progress_stage = "stalled"
                                job.progress_percent = min(int(job.progress_percent or 0), 95)
                                job.estimated_time_left = None
                                job.error_message = (
                                    "Transcription stalled (exceeded expected duration)"
                                )
                                job.stalled_at = now
                                changed = True
                        if changed:
                            await session.commit()
                except Exception as exc:
                    self._logger.warning("Watchdog encountered an error: %s", exc)
                    continue
        except asyncio.CancelledError:
            return


# Global singleton for app lifetime
queue = TranscriptionJobQueue(concurrency=3)


async def resume_queued_jobs(queue_obj: TranscriptionJobQueue) -> int:
    """Re-enqueue any jobs that were left in queued status when the app restarts."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Job.id).where(Job.status == "queued"))
        job_ids = result.scalars().all()

    for job_id in job_ids:
        await queue_obj.enqueue(str(job_id))

    return len(job_ids)
