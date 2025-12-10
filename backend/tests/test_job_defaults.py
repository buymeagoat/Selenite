import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.provider_manager import ProviderManager
from app.utils.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_job_creation_uses_user_settings_defaults(monkeypatch):
    # Set up fresh schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        monkeypatch.setattr(ProviderManager, "get_snapshot", lambda: {"asr": [], "diarizers": []})
        async with AsyncSessionLocal() as db:
            user = User(
                username="defaultsuser",
                email="d@example.com",
                hashed_password=hash_password("XyZ12345!!"),
            )
            db.add(user)
            await db.flush()
            settings = UserSettings(user_id=user.id, default_model="small", default_language="en")
            db.add(settings)
            await db.commit()
            token = create_access_token(data={"user_id": user.id, "username": user.username})
            auth_headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/jobs",
                headers=auth_headers,
                files={"file": ("sample.wav", b"fake-audio", "audio/wav")},
                data={"enable_timestamps": "true", "enable_speaker_detection": "true"},
            )
            assert resp.status_code == 400
            assert "No ASR models available" in resp.json()["detail"]
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
