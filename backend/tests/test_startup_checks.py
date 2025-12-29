"""Tests for startup checks seeding behavior."""

import pytest
from sqlalchemy import delete, func, select

from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.models.system_preferences import SystemPreferences
from app.models.model_provider import ModelSet, ModelEntry
from app.models.tag import Tag
from app.startup_checks import _DEFAULT_TAGS, _CURATED, ensure_core_tables


@pytest.fixture
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_default_tags_seeded_once(test_db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "model_storage_path", str(tmp_path / "models"))

    await ensure_core_tables()

    async with AsyncSessionLocal() as session:
        tag_count = (await session.execute(select(func.count(Tag.id)))).scalar_one()
        assert tag_count == len(_DEFAULT_TAGS)
        prefs = await session.get(SystemPreferences, 1)
        assert prefs.default_tags_seeded is True

    await ensure_core_tables()

    async with AsyncSessionLocal() as session:
        tag_count = (await session.execute(select(func.count(Tag.id)))).scalar_one()
        assert tag_count == len(_DEFAULT_TAGS)
        await session.execute(delete(Tag))
        await session.commit()

    await ensure_core_tables()

    async with AsyncSessionLocal() as session:
        tag_count = (await session.execute(select(func.count(Tag.id)))).scalar_one()
        assert tag_count == 0


@pytest.mark.asyncio
async def test_curated_registry_seeded_when_missing(test_db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "model_storage_path", str(tmp_path / "models"))

    async with AsyncSessionLocal() as session:
        set_path = tmp_path / "models" / "custom-set"
        set_path.mkdir(parents=True, exist_ok=True)
        model_set = ModelSet(
            type="asr",
            name="custom-set",
            description="custom",
            abs_path=str(set_path),
            enabled=True,
        )
        session.add(model_set)
        await session.flush()
        entry_path = set_path / "custom-entry"
        entry_path.mkdir(parents=True, exist_ok=True)
        session.add(
            ModelEntry(
                set_id=model_set.id,
                type="asr",
                name="custom-entry",
                description="custom entry",
                abs_path=str(entry_path),
                enabled=True,
            )
        )
        await session.commit()

    await ensure_core_tables()

    curated_sample = next(iter(_CURATED["asr"].keys()))
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ModelSet).where(ModelSet.type == "asr", ModelSet.name == curated_sample)
        )
        assert result.scalar_one_or_none() is not None
