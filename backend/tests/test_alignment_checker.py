"""Tests for alignment drift detection helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import AsyncSessionLocal, Base, engine
from app.models.model_provider import ModelEntry, ModelSet
from app.utils.alignment import AlignmentChecker


@pytest.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_set(session, *, path: Path) -> ModelSet:
    model_set = ModelSet(
        type="asr",
        name="legacy",
        description=None,
        abs_path=str(path),
        enabled=True,
        disable_reason=None,
    )
    session.add(model_set)
    await session.commit()
    await session.refresh(model_set)
    return model_set


@pytest.mark.anyio
async def test_registry_path_violation_detected(tmp_path: Path):
    canonical_root = tmp_path / "backend/models"
    canonical_root.mkdir(parents=True)
    legacy_path = tmp_path / "models/legacy"
    legacy_path.mkdir(parents=True)

    async with AsyncSessionLocal() as session:
        model_set = await _create_set(session, path=legacy_path)
        session.add(
            ModelEntry(
                set_id=model_set.id,
                type="asr",
                name="bad-entry",
                description=None,
                abs_path=str(legacy_path / "entry"),
                enabled=True,
                disable_reason=None,
            )
        )
        await session.commit()

        checker = AlignmentChecker(
            model_root=canonical_root,
            storage_root=tmp_path / "storage",
            backend_root=tmp_path / "backend",
            project_root=tmp_path,
            media_path=tmp_path / "storage/media",
            transcript_path=tmp_path / "storage/transcripts",
        )
        issues = await checker.check_registry_paths(session)

    assert any("legacy" in issue.detail for issue in issues)
    assert any("bad-entry" in issue.detail for issue in issues)


@pytest.mark.anyio
async def test_filesystem_duplicate_detected(tmp_path: Path):
    canonical_root = tmp_path / "backend/models"
    canonical_root.mkdir(parents=True)
    legacy_root = tmp_path / "models"
    (legacy_root / "ghost").mkdir(parents=True)

    backend_storage = tmp_path / "backend/storage"
    backend_storage.mkdir(parents=True)
    (backend_storage / "stale.txt").write_text("x", encoding="utf-8")

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True)
    checker = AlignmentChecker(
        model_root=canonical_root,
        storage_root=storage_root,
        backend_root=tmp_path / "backend",
        project_root=tmp_path,
        media_path=storage_root / "media",
        transcript_path=storage_root / "transcripts",
    )

    issues = checker.check_filesystem()
    assert any(issue.category == "legacy_models" for issue in issues)
    assert any(issue.category == "backend_storage" for issue in issues)
