"""Simple in-memory async job queue with concurrency limit for transcription jobs.

This is a simulated queue suitable for Increment 5 testing.
In later increments, this can be replaced or enhanced.
"""

import asyncio
from typing import Set

from app.database import AsyncSessionLocal
from app.services.transcription import process_transcription_job


class TranscriptionJobQueue:
    def __init__(self, concurrency: int = 3):
        self._queue: "asyncio.Queue[tuple[str, bool]]" = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running_ids: Set[str] = set()
        self._concurrency = concurrency
        self._started = False

    async def start(self):
        if self._started:
            return
        self._started = True
        for _ in range(self._concurrency):
            self._workers.append(asyncio.create_task(self._worker()))

    async def stop(self):
        # Graceful stop: put sentinel values
        for _ in self._workers:
            await self._queue.put(("__STOP__", False))
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False

    async def _worker(self):
        while True:
            job_id, should_fail = await self._queue.get()
            if job_id == "__STOP__":  # sentinel
                break
            # Skip if already running (duplicate enqueue)
            if job_id in self._running_ids:
                self._queue.task_done()
                continue
            self._running_ids.add(job_id)
            try:
                async with AsyncSessionLocal() as db:
                    await process_transcription_job(job_id, db, should_fail=should_fail)
                    await db.commit()  # Ensure changes are committed
            except Exception:
                pass  # Errors logged within process_transcription_job
            finally:
                self._running_ids.discard(job_id)
                self._queue.task_done()

    async def enqueue(self, job_id: str, *, should_fail: bool = False) -> None:
        # Avoid duplicate enqueues if already queued or running: check running set only
        if job_id in self._running_ids:
            return
        # Ensure workers are started even if startup event didn't run (e.g., tests)
        if not self._started:
            await self.start()
        await self._queue.put((job_id, should_fail))


# Global singleton for app lifetime
queue = TranscriptionJobQueue(concurrency=3)
