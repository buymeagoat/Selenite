"""Tests for job action endpoints: cancel, restart, tag assign/remove, settings get/update."""

import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import BACKEND_ROOT
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.job import Job
from app.utils.security import hash_password, create_access_token
from app.schemas.model_registry import ModelSetCreate, ModelWeightCreate
from app.services.model_registry import ModelRegistryService
from app.services.provider_manager import ProviderManager


@pytest.fixture(scope="function")
async def test_db():
    """Create test database for each test function."""
    # Clean up before creating to ensure fresh state
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user - will get ID=1 as first user
        user = User(
            username="jobactions",
            email="jobactions@example.com",
            hashed_password=hash_password("InitialPass123"),
        )
        session.add(user)
        await session.commit()

        # Seed a minimal ASR model in the registry so jobs can be created
        models_root = BACKEND_ROOT / "models"
        set_path = models_root / "test-set"
        entry_path = set_path / "test-entry" / "model.bin"
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text("ok", encoding="utf-8")

        model_set = await ModelRegistryService.create_model_set(
            session,
            ModelSetCreate(type="asr", name="test-set", abs_path=str(set_path.resolve())),
            actor="system",
        )
    await ModelRegistryService.create_model_weight(
        session,
        model_set,
        ModelWeightCreate(
            name="test-entry",
            description="seed entry",
            abs_path=str(entry_path.resolve()),
            checksum=None,
        ),
        actor="system",
    )

    # Refresh provider cache for tests
    await ProviderManager.refresh(session)

    yield

    # Clean up after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_headers():
    token = create_access_token(data={"user_id": 1, "username": "jobactions"})
    return {"Authorization": f"Bearer {token}"}


async def _create_job_via_api(client: AsyncClient, auth_headers) -> str:
    file_content = b"fake audio content"
    files = {"file": ("sample.wav", io.BytesIO(file_content), "audio/wav")}
    resp = await client.post("/jobs", files=files, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_cancel_job_success(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        resp = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_pause_job_from_queued(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        resp = await client.post(f"/jobs/{job_id}/pause", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_job_from_processing_sets_pausing(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            job.status = "processing"
            await session.commit()
        resp = await client.post(f"/jobs/{job_id}/pause", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pausing"


@pytest.mark.asyncio
async def test_pause_job_rejected_during_diarization(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            job.status = "processing"
            job.progress_stage = "diarizing"
            await session.commit()
        resp = await client.post(f"/jobs/{job_id}/pause", headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Job cannot be paused during diarization"


@pytest.mark.asyncio
async def test_resume_job_from_paused(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        pause_resp = await client.post(f"/jobs/{job_id}/pause", headers=auth_headers)
        assert pause_resp.status_code == 200
        resp = await client.post(f"/jobs/{job_id}/resume", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_cancel_job_invalid_status(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        # Mark job completed directly
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            job.status = "completed"
            await session.commit()
        resp = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_restart_job_from_completed(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            job.status = "completed"
            await session.commit()
        resp = await client.post(f"/jobs/{job_id}/restart", headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert data["id"] != job_id


@pytest.mark.asyncio
async def test_tag_assign_and_remove(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_id = await _create_job_via_api(client, auth_headers)
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            job.status = "completed"  # allow restart/tag operations
            await session.commit()
        # First create the tag
        tag_resp = await client.post(
            "/tags",
            headers=auth_headers,
            json={"name": "Urgent", "color": "#FF0000"},
        )
        assert tag_resp.status_code == 201
        tag_id = tag_resp.json()["id"]
        # Then assign it to the job
        assign_resp = await client.post(
            f"/jobs/{job_id}/tags",
            headers=auth_headers,
            json={"tag_ids": [tag_id]},
        )
        assert assign_resp.status_code == 200
        tags = assign_resp.json()["tags"]
        assert any(t["id"] == tag_id and t["name"] == "Urgent" for t in tags)
        # Remove the tag
        remove_resp = await client.delete(f"/jobs/{job_id}/tags/{tag_id}", headers=auth_headers)
        assert remove_resp.status_code == 200
        remove_data = remove_resp.json()
        assert remove_data["message"] == "Tag removed from job"
        assert remove_data["tag_id"] == tag_id


@pytest.mark.asyncio
async def test_settings_get_and_update(test_db, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        get_resp = await client.get("/settings", headers=auth_headers)
        assert get_resp.status_code == 200
        defaults = get_resp.json()
        assert defaults["default_model"] == "medium"
        assert defaults["default_language"] == "auto"
        assert defaults["max_concurrent_jobs"] == 3
        put_resp = await client.put(
            "/settings",
            headers=auth_headers,
            json={
                "default_asr_provider": "test-set",
                "default_model": "test-entry",
                "default_language": "en",
                "max_concurrent_jobs": 2,
            },
        )
        assert put_resp.status_code == 200
        updated = put_resp.json()
        assert updated["default_model"] == "test-entry"
        assert updated["default_language"] == "en"
        assert updated["max_concurrent_jobs"] == 2
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                UserSettings.__table__.select().where(UserSettings.default_model == "test-entry")
            )
            assert res.first() is not None
