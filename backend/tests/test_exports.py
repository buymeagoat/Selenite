"""Tests for export endpoints."""

import pytest
import uuid
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.config import settings
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.job import Job
from app.models.transcript import Transcript
from app.utils.security import create_access_token, hash_password
from sqlalchemy import select


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user
        test_user = User(
            id=1,
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("changeme"),
        )
        session.add(test_user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def auth_token():
    """Generate a valid JWT token for test user."""
    token = create_access_token(data={"user_id": 1, "username": "admin"})
    return token


@pytest.fixture
async def client(test_db, auth_token):
    """Create test client with authentication."""
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {auth_token}"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac


@pytest.fixture
async def db():
    """Provide database session."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def sample_job_id(db: AsyncSession):
    """Create a completed job with transcript for testing."""
    job_id = str(uuid.uuid4())

    # Create job
    job = Job(
        id=job_id,
        user_id=1,
        original_filename="test-recording.mp3",
        saved_filename=f"{job_id}.mp3",
        file_path=f"/tmp/{job_id}.mp3",
        file_size=1024000,
        mime_type="audio/mpeg",
        status="completed",
        duration=120.0,
        language_detected="en",
        model_used="base",
        speaker_count=2,
    )
    db.add(job)

    # Create transcript file
    transcript_dir = Path(settings.transcript_storage_path)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / f"{job_id}.txt"
    transcript_path.write_text("This is a test transcript.", encoding="utf-8")

    job.transcript_path = str(transcript_path)

    # Create transcript record
    transcript = Transcript(
        job_id=job_id,
        format="txt",
        file_path=str(transcript_path),
        file_size=transcript_path.stat().st_size,
    )
    db.add(transcript)

    await db.commit()

    yield job_id

    # Cleanup
    if transcript_path.exists():
        transcript_path.unlink()


@pytest.mark.asyncio
async def test_export_txt(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as plain text."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=txt")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert response.text  # Should have content


@pytest.mark.asyncio
async def test_export_json(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as JSON."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert "job_id" in data
    assert "filename" in data
    assert "text" in data
    assert "segments" in data


@pytest.mark.asyncio
async def test_export_srt(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as SRT subtitles."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=srt")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert ".srt" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_vtt(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as WebVTT subtitles."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=vtt")
    assert response.status_code == 200
    assert "text/vtt" in response.headers["content-type"]
    assert "WEBVTT" in response.text


@pytest.mark.asyncio
async def test_export_md(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as Markdown."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=md")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "##" in response.text  # Should have Markdown headings


@pytest.mark.asyncio
async def test_export_docx(client: AsyncClient, sample_job_id: str):
    """Test exporting transcript as DOCX."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=docx")
    assert response.status_code == 200
    assert "officedocument.wordprocessingml" in response.headers["content-type"]
    assert ".docx" in response.headers["content-disposition"]
    assert len(response.content) > 0  # Should have binary content


@pytest.mark.asyncio
async def test_export_invalid_format(client: AsyncClient, sample_job_id: str):
    """Test exporting with invalid format returns 400."""
    response = await client.get(f"/jobs/{sample_job_id}/export?format=invalid")
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_export_nonexistent_job(client: AsyncClient):
    """Test exporting nonexistent job returns 404."""
    response = await client.get("/jobs/00000000-0000-0000-0000-000000000000/export")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_incomplete_job(client: AsyncClient, db: AsyncSession):
    """Test exporting incomplete job returns 400."""
    from app.models.job import Job
    from app.models.user import User
    import uuid

    # Get test user
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one()

    # Create incomplete job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        user_id=user.id,
        original_filename="test.mp3",
        saved_filename=f"{job_id}.mp3",
        file_path="/tmp/test.mp3",
        file_size=1024,
        mime_type="audio/mpeg",
        status="processing",  # Not completed
    )
    db.add(job)
    await db.commit()

    response = await client.get(f"/jobs/{job_id}/export?format=txt")
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_export_default_format(client: AsyncClient, sample_job_id: str):
    """Test export defaults to txt format when not specified."""
    response = await client.get(f"/jobs/{sample_job_id}/export")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
