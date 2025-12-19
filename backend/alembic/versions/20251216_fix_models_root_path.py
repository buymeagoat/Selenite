"""Move model registry paths under backend/models and migrate DB records."""

from __future__ import annotations

import shutil
from pathlib import Path

from alembic import op
from sqlalchemy import inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import BACKEND_ROOT, PROJECT_ROOT
from app.models.model_provider import ModelEntry, ModelSet

# revision identifiers, used by Alembic.
revision = "20251216_fix_models_root_path"
down_revision = "20251214_last_selected_registry_sets"
branch_labels = None
depends_on = None


def _legacy_models_root() -> Path:
    return (PROJECT_ROOT / "models").resolve()


def _canonical_models_root() -> Path:
    return (BACKEND_ROOT / "models").resolve()


def upgrade() -> None:
    legacy_root = _legacy_models_root()
    target_root = _canonical_models_root()
    bind = op.get_bind()
    inspector = inspect(bind)

    # Guard against stale databases that never created the registry tables.
    if "model_sets" not in inspector.get_table_names():
        ModelSet.__table__.create(bind, checkfirst=True)
    if "model_entries" not in inspector.get_table_names():
        ModelEntry.__table__.create(bind, checkfirst=True)

    session = Session(bind=bind)

    # Move on-disk directories if they still live under the legacy project-level path.
    if legacy_root.exists() and legacy_root != target_root:
        target_root.mkdir(parents=True, exist_ok=True)
        for provider_dir in legacy_root.iterdir():
            dest = target_root / provider_dir.name
            if dest.exists():
                continue
            try:
                shutil.move(str(provider_dir), str(dest))
            except shutil.Error:
                # If move fails (permissions, etc.), continue so DB still updates.
                continue

        # Clean up legacy root if empty
        try:
            next(legacy_root.iterdir())
        except StopIteration:
            legacy_root.rmdir()

    legacy_prefix = str(legacy_root)
    target_prefix = str(target_root)

    try:
        try:
            sets = session.execute(select(ModelSet)).scalars().all()
            entries = session.execute(select(ModelEntry)).scalars().all()
        except OperationalError:
            session.rollback()
            return

        changed = False

        for model_set in sets:
            if model_set.abs_path and model_set.abs_path.startswith(legacy_prefix):
                suffix = model_set.abs_path[len(legacy_prefix) :].lstrip("/\\")  # type: ignore[arg-type]
                new_path = Path(target_prefix) / suffix
                model_set.abs_path = str(new_path.resolve())
                changed = True

        for entry in entries:
            if entry.abs_path and entry.abs_path.startswith(legacy_prefix):
                suffix = entry.abs_path[len(legacy_prefix) :].lstrip("/\\")  # type: ignore[arg-type]
                new_path = Path(target_prefix) / suffix
                entry.abs_path = str(new_path.resolve())
                changed = True

        if changed:
            session.commit()
    finally:
        session.close()


def downgrade() -> None:
    # No-op: we don't want to move paths back to the legacy root.
    pass
