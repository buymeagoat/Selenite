"""E2E test database seeding script.

Creates sample jobs and tags for E2E testing purposes.
Usage: python -m app.seed_e2e
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.job import Job
from app.models.tag import Tag
from app.models.transcript import Transcript
from app.utils.security import hash_password
from sqlalchemy import select, delete


async def clear_test_data():
    """Clear existing test data (except admin user)."""
    print("Clearing existing test data...")
    async with AsyncSessionLocal() as db:
        # Delete jobs (cascades to transcripts and job_tags)
        await db.execute(delete(Job))
        # Delete tags
        await db.execute(delete(Tag))
        # Delete users (force clean slate) and will recreate admin
        await db.execute(delete(User))
        await db.commit()
    print("Test data cleared.")


async def seed_e2e_database():
    """Seed database with E2E test data."""
    print("Seeding E2E test database...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Ensure admin user exists
        result = await db.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@selenite.local",
                hashed_password=hash_password("changeme"),
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            print("Created admin user")
        else:
            # Always reset admin password for deterministic E2E runs
            setattr(admin_user, "hashed_password", hash_password("changeme"))
            await db.commit()
            await db.refresh(admin_user)
            print("Reset admin user password to default for E2E")
        print("Admin user present:", admin_user.username)

        # Ensure admin has settings
        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == admin_user.id)
        )
        admin_settings = settings_result.scalar_one_or_none()
        if not admin_settings:
            admin_settings = UserSettings(user_id=admin_user.id)
            db.add(admin_settings)
            await db.commit()
            print("Created admin user settings")

        # Create sample tags
        tags = []
        tag_data = [
            {"name": "Meeting", "color": "#4CAF50"},
            {"name": "Interview", "color": "#2196F3"},
            {"name": "Podcast", "color": "#FF9800"},
            {"name": "Lecture", "color": "#9C27B0"},
            {"name": "Important", "color": "#F44336"},
        ]

        for tag_info in tag_data:
            tag = Tag(**tag_info)
            db.add(tag)
            tags.append(tag)

        await db.commit()
        for tag in tags:
            await db.refresh(tag)
        print(f"Created {len(tags)} tags")

        # Create sample jobs with various statuses
        jobs = []
        now = datetime.utcnow()

        # Completed jobs
        for i in range(5):
            job_id = str(uuid.uuid4())
            job = Job(
                id=job_id,
                user_id=admin_user.id,
                original_filename=f"meeting-recording-{i+1}.mp3",
                saved_filename=f"{job_id}.mp3",
                file_path=f"/storage/uploads/{job_id}.mp3",
                file_size=1024000 + (i * 100000),
                mime_type="audio/mpeg",
                duration=300.0 + (i * 60),
                status="completed",
                progress_percent=100,
                progress_stage="finalizing",
                model_used="base",
                language_detected="English",
                speaker_count=2,
                has_timestamps=True,
                has_speaker_labels=True,
                transcript_path=f"/storage/transcripts/{job_id}.txt",
                created_at=now - timedelta(days=i + 1),
                started_at=now - timedelta(days=i + 1, hours=23, minutes=50),
                completed_at=now - timedelta(days=i + 1, hours=23, minutes=40),
            )
            db.add(job)
            jobs.append(job)

            # Add transcript
            transcript = Transcript(
                job_id=job_id,
                format="txt",
                file_path=f"/storage/transcripts/{job_id}.txt",
                file_size=5000 + (i * 500),
            )
            db.add(transcript)

        # Processing jobs
        for i in range(2):
            job_id = str(uuid.uuid4())
            job = Job(
                id=job_id,
                user_id=admin_user.id,
                original_filename=f"interview-{i+1}.wav",
                saved_filename=f"{job_id}.wav",
                file_path=f"/storage/uploads/{job_id}.wav",
                file_size=2048000 + (i * 200000),
                mime_type="audio/wav",
                duration=600.0 + (i * 120),
                status="processing",
                progress_percent=45 + (i * 10),
                progress_stage="transcribing",
                estimated_time_left=120 - (i * 30),
                model_used="medium",
                language_detected="English",
                speaker_count=1,
                has_timestamps=True,
                has_speaker_labels=False,
                created_at=now - timedelta(hours=i + 1),
                started_at=now - timedelta(hours=i + 1, minutes=-5),
            )
            db.add(job)
            jobs.append(job)

        # Queued job
        job_id = str(uuid.uuid4())
        queued_job = Job(
            id=job_id,
            user_id=admin_user.id,
            original_filename="podcast-episode.mp3",
            saved_filename=f"{job_id}.mp3",
            file_path=f"/storage/uploads/{job_id}.mp3",
            file_size=5120000,
            mime_type="audio/mpeg",
            duration=1800.0,
            status="queued",
            progress_percent=0,
            progress_stage=None,
            model_used="medium",
            has_timestamps=True,
            has_speaker_labels=True,
            created_at=now - timedelta(minutes=5),
        )
        db.add(queued_job)
        jobs.append(queued_job)

        # Failed job
        job_id = str(uuid.uuid4())
        failed_job = Job(
            id=job_id,
            user_id=admin_user.id,
            original_filename="corrupted-file.mp4",
            saved_filename=f"{job_id}.mp4",
            file_path=f"/storage/uploads/{job_id}.mp4",
            file_size=512000,
            mime_type="video/mp4",
            duration=None,
            status="failed",
            progress_percent=15,
            progress_stage="loading_model",
            error_message="Failed to decode audio stream: unsupported format",
            model_used="medium",
            created_at=now - timedelta(hours=2),
            started_at=now - timedelta(hours=2, minutes=-2),
        )
        db.add(failed_job)
        jobs.append(failed_job)

        await db.commit()

        # Refresh jobs and assign tags
        print("Assigning tags to jobs...")
        for job in jobs[:5]:  # Tag first 5 completed jobs
            await db.refresh(job)

        for i, job in enumerate(jobs[:5]):
            if i % 2 == 0:
                # Use text() for raw SQL
                await db.execute(
                    text(
                        f"INSERT OR IGNORE INTO job_tags (job_id, tag_id) VALUES ('{job.id}', {tags[0].id})"
                    )
                )
            if i % 3 == 0:
                await db.execute(
                    text(
                        f"INSERT OR IGNORE INTO job_tags (job_id, tag_id) VALUES ('{job.id}', {tags[4].id})"
                    )
                )

        await db.commit()
        print(f"Created {len(jobs)} jobs with various statuses")
        print(f"  - {sum(1 for j in jobs if j.status == 'completed')} completed")
        print(f"  - {sum(1 for j in jobs if j.status == 'processing')} processing")
        print(f"  - {sum(1 for j in jobs if j.status == 'queued')} queued")
        print(f"  - {sum(1 for j in jobs if j.status == 'failed')} failed")

    print("\nE2E database seeding complete.")
    print("\nTest data summary:")
    print("  User: admin / changeme")
    print(f"  Tags: {len(tag_data)} tags created")
    print(f"  Jobs: {len(jobs)} jobs with transcripts")


if __name__ == "__main__":
    import sys

    if "--clear" in sys.argv:
        asyncio.run(clear_test_data())
    else:
        asyncio.run(seed_e2e_database())
