"""Tests for database connection and models."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, Base, AsyncSessionLocal
from app.models import User, Job, Tag, Transcript


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with AsyncSessionLocal() as session:
        yield session

    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can connect to the database."""
    async with engine.begin() as conn:
        assert conn is not None
        # Try a simple query
        result = await conn.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_create_tables(db_session: AsyncSession):
    """Test that all tables are created correctly."""
    # Verify tables exist by checking metadata
    assert "users" in Base.metadata.tables
    assert "jobs" in Base.metadata.tables
    assert "tags" in Base.metadata.tables
    assert "transcripts" in Base.metadata.tables
    assert "job_tags" in Base.metadata.tables


@pytest.mark.asyncio
async def test_user_model(db_session: AsyncSession):
    """Test User model creation."""
    user = User(username="testuser", email="test@example.com", hashed_password="hashedpassword123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_job_model(db_session: AsyncSession):
    """Test Job model creation."""
    # Create a user first
    user = User(username="jobuser", email="job@example.com", hashed_password="hashed123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a job
    job = Job(
        id="550e8400-e29b-41d4-a716-446655440000",
        user_id=user.id,
        original_filename="test.mp3",
        saved_filename="550e8400.mp3",
        file_path="/storage/media/550e8400.mp3",
        status="queued",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.id == "550e8400-e29b-41d4-a716-446655440000"
    assert job.original_filename == "test.mp3"
    assert job.status == "queued"
    assert job.progress_percent == 0


@pytest.mark.asyncio
async def test_tag_model(db_session: AsyncSession):
    """Test Tag model creation."""
    tag = Tag(name="interviews", color="#2D6A4F")
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)

    assert tag.id is not None
    assert tag.name == "interviews"
    assert tag.color == "#2D6A4F"


@pytest.mark.asyncio
async def test_job_tag_relationship(db_session: AsyncSession):
    """Test many-to-many relationship between jobs and tags."""
    from sqlalchemy.orm import selectinload

    # Create user
    user = User(username="reluser", hashed_password="hash123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create tags
    tag1 = Tag(name="tag1", color="#111111")
    tag2 = Tag(name="tag2", color="#222222")
    db_session.add_all([tag1, tag2])
    await db_session.commit()
    await db_session.refresh(tag1)
    await db_session.refresh(tag2)

    # Create job with tags
    job = Job(
        id="test-job-id",
        user_id=user.id,
        original_filename="test.mp3",
        saved_filename="test.mp3",
        file_path="/path/test.mp3",
        status="queued",
    )
    job.tags.append(tag1)
    job.tags.append(tag2)
    db_session.add(job)
    await db_session.commit()

    # Reload job with tags eagerly loaded
    result = await db_session.execute(
        select(Job).where(Job.id == "test-job-id").options(selectinload(Job.tags))
    )
    job = result.scalar_one()

    assert len(job.tags) == 2
    assert any(t.name == "tag1" for t in job.tags)
    assert any(t.name == "tag2" for t in job.tags)


@pytest.mark.asyncio
async def test_transcript_model(db_session: AsyncSession):
    """Test Transcript model creation."""
    # Create user and job first
    user = User(username="transuser", hashed_password="hash123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    job = Job(
        id="trans-job-id",
        user_id=user.id,
        original_filename="test.mp3",
        saved_filename="test.mp3",
        file_path="/path/test.mp3",
        status="completed",
    )
    db_session.add(job)
    await db_session.commit()

    # Create transcript
    transcript = Transcript(
        job_id=job.id, format="txt", file_path="/transcripts/trans-job-id.txt", file_size=1024
    )
    db_session.add(transcript)
    await db_session.commit()
    await db_session.refresh(transcript)

    assert transcript.id is not None
    assert transcript.job_id == job.id
    assert transcript.format == "txt"
