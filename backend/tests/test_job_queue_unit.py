"""Unit tests for TranscriptionJobQueue internals."""

import asyncio
from types import SimpleNamespace

import pytest

from app.services.job_queue import TranscriptionJobQueue
import app.services.job_queue as job_queue_module


class DummySession:
    """AsyncSession stub used to avoid touching the real database."""

    def __init__(self):
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_enqueue_processes_job_once(monkeypatch):
    """Ensure enqueue triggers process_transcription_job exactly once per ID."""
    calls: list[tuple[str, bool]] = []

    async def fake_process(job_id, db, should_fail=False):
        calls.append((job_id, should_fail))

    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(job_queue_module, "process_transcription_job", fake_process)

    queue = TranscriptionJobQueue(concurrency=1)
    await queue.start()

    await queue.enqueue("job-1")
    assert queue._queue is not None
    await asyncio.wait_for(queue._queue.join(), timeout=1)

    assert calls == [("job-1", False)]

    # Mark running to simulate in-flight job; enqueue should no-op.
    queue._running_ids.add("job-1")
    await queue.enqueue("job-1")
    assert queue._queue.qsize() == 0
    queue._running_ids.clear()

    await queue.stop()


@pytest.mark.asyncio
async def test_enqueue_skips_when_testing(monkeypatch):
    """When not started and settings.is_testing is True, enqueue should no-op."""
    queue = TranscriptionJobQueue()
    monkeypatch.setattr(job_queue_module, "settings", SimpleNamespace(is_testing=True))

    await queue.enqueue("job-x")

    assert queue._queue is None
    assert not queue._started


@pytest.mark.asyncio
async def test_enqueue_autostarts_when_not_testing(monkeypatch):
    """Enqueue should spawn workers when not testing."""
    queue = TranscriptionJobQueue()
    monkeypatch.setattr(job_queue_module, "settings", SimpleNamespace(is_testing=False))
    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())

    async def fake_process(job_id, db, should_fail=False):
        return None

    monkeypatch.setattr(job_queue_module, "process_transcription_job", fake_process)

    await queue.enqueue("auto-job")
    assert queue._started is True
    assert queue._queue is not None
    await asyncio.wait_for(queue._queue.join(), timeout=1)
    await queue.stop()


@pytest.mark.asyncio
async def test_set_concurrency_restarts_workers(monkeypatch):
    """Changing concurrency restarts workers and updates worker count."""
    monkeypatch.setattr(job_queue_module, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        job_queue_module, "process_transcription_job", lambda *args, **kwargs: asyncio.sleep(0)
    )

    queue = TranscriptionJobQueue(concurrency=1)
    await queue.start()
    assert len(queue._workers) == 1

    await queue.set_concurrency(2)
    assert queue._concurrency == 2
    assert len(queue._workers) == 2

    await queue.stop()


@pytest.mark.asyncio
async def test_set_concurrency_rejects_invalid():
    """Concurrency must be >=1."""
    queue = TranscriptionJobQueue()
    with pytest.raises(ValueError):
        await queue.set_concurrency(0)


@pytest.mark.asyncio
async def test_stop_handles_event_loop_closed(monkeypatch):
    """Simulate RuntimeError during stop to hit defensive branch."""
    queue = TranscriptionJobQueue()

    class FakeQueue:
        async def put(self, item):
            raise RuntimeError("Event loop is closed")

    queue._queue = FakeQueue()
    queue._workers = [object(), object()]

    async def fake_gather(*args, **kwargs):
        return None

    monkeypatch.setattr(asyncio, "gather", fake_gather)
    await queue.stop()
    assert queue._queue is None


@pytest.mark.asyncio
async def test_set_concurrency_handles_loop_closed(monkeypatch):
    """If stop raises RuntimeError loop closed, state should reset."""
    queue = TranscriptionJobQueue(concurrency=1)

    async def fake_stop():
        raise RuntimeError("Event loop is closed")

    queue.stop = fake_stop  # type: ignore[assignment]

    def raise_runtime():
        raise RuntimeError("no loop")

    monkeypatch.setattr("asyncio.get_running_loop", raise_runtime)
    await queue.set_concurrency(2)
    assert queue._started is False
    assert queue._queue is None
