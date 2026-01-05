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
from app.models.model_provider import ModelEntry, ModelSet
from app.models.job import Job
from app.models.tag import Tag
from app.models.transcript import Transcript
from app.utils.security import hash_password
from sqlalchemy import select, delete
from app.config import BACKEND_ROOT


async def clear_test_data():
    """Clear existing test data (except admin user)."""
    print("Clearing existing test data...")
    async with engine.begin() as conn:
        # Ensure tables exist even on a fresh workspace so deletes don't fail
        await conn.run_sync(Base.metadata.create_all)
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
                is_admin=True,
                is_disabled=False,
                force_password_reset=False,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            print("Created admin user")
        else:
            # Always reset admin password for deterministic E2E runs
            setattr(admin_user, "hashed_password", hash_password("changeme"))
            if admin_user.email != "admin@selenite.local":
                admin_user.email = "admin@selenite.local"
            if not admin_user.is_admin:
                admin_user.is_admin = True
            if admin_user.is_disabled:
                admin_user.is_disabled = False
            if admin_user.force_password_reset:
                admin_user.force_password_reset = False
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

        # Ensure E2E model registry defaults (so UI + tests can select enabled weights)
        model_root = (BACKEND_ROOT / "models").resolve()
        e2e_asr_root = model_root / "e2e-asr"
        e2e_asr_weight = e2e_asr_root / "base"
        e2e_diar_root = model_root / "e2e-diarizer"
        e2e_diar_weight = e2e_diar_root / "diar-weight"

        for path in (e2e_asr_weight, e2e_diar_weight):
            path.mkdir(parents=True, exist_ok=True)
            placeholder = path / ".e2e-placeholder"
            if not placeholder.exists():
                placeholder.write_text("e2e test weight placeholder\n", encoding="utf-8")

        asr_set = (
            await db.execute(
                select(ModelSet).where(ModelSet.type == "asr").where(ModelSet.name == "e2e-asr")
            )
        ).scalar_one_or_none()
        if not asr_set:
            asr_set = ModelSet(
                type="asr",
                name="e2e-asr",
                description="E2E test ASR set",
                abs_path=str(e2e_asr_root),
                enabled=True,
            )
            db.add(asr_set)
            await db.commit()
            await db.refresh(asr_set)

        diar_set = (
            await db.execute(
                select(ModelSet)
                .where(ModelSet.type == "diarizer")
                .where(ModelSet.name == "e2e-diarizer")
            )
        ).scalar_one_or_none()
        if not diar_set:
            diar_set = ModelSet(
                type="diarizer",
                name="e2e-diarizer",
                description="E2E test diarizer set",
                abs_path=str(e2e_diar_root),
                enabled=True,
            )
            db.add(diar_set)
            await db.commit()
            await db.refresh(diar_set)

        asr_weight = (
            await db.execute(
                select(ModelEntry)
                .where(ModelEntry.set_id == asr_set.id)
                .where(ModelEntry.name == "base")
            )
        ).scalar_one_or_none()
        if not asr_weight:
            asr_weight = ModelEntry(
                set_id=asr_set.id,
                type="asr",
                name="base",
                description="E2E base ASR weight",
                abs_path=str(e2e_asr_weight),
                enabled=True,
            )
            db.add(asr_weight)

        diar_weight = (
            await db.execute(
                select(ModelEntry)
                .where(ModelEntry.set_id == diar_set.id)
                .where(ModelEntry.name == "diar-weight")
            )
        ).scalar_one_or_none()
        if not diar_weight:
            diar_weight = ModelEntry(
                set_id=diar_set.id,
                type="diarizer",
                name="diar-weight",
                description="E2E diarizer weight",
                abs_path=str(e2e_diar_weight),
                enabled=True,
            )
            db.add(diar_weight)

        if admin_settings:
            admin_settings.default_asr_provider = "e2e-asr"
            admin_settings.default_model = "base"
            admin_settings.default_diarizer_provider = "e2e-diarizer"
            admin_settings.default_diarizer = "diar-weight"

        await db.commit()

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
