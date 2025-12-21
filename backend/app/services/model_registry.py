"""Business logic for the model registry."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import BACKEND_ROOT, PROJECT_ROOT
from app.models.system_preferences import SystemPreferences
from app.models.model_provider import ModelEntry, ModelSet
from app.schemas.model_registry import (
    ModelWeightCreate,
    ModelWeightUpdate,
    ModelSetCreate,
    ModelSetUpdate,
)
from app.services.provider_manager import ProviderManager
from app.utils.memorialization import write_registry_event


class ModelRegistryService:
    """Service helpers for CRUD operations on model sets and weights."""

    _MODELS_ROOT = (BACKEND_ROOT / "models").resolve()
    _LEGACY_MODELS_ROOT = (PROJECT_ROOT / "models").resolve()
    _SEEDED_SET_REASON = "Seeded provider; add weights to enable."
    _SEEDED_WEIGHT_REASON = "Weights not present; drop files then enable."
    _FORCE_ENABLED_REASON = "Force enabled without weight files."

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    @classmethod
    async def list_model_sets(cls, session: AsyncSession) -> list[ModelSet]:
        stmt = (
            select(ModelSet)
            .options(selectinload(ModelSet.entries))
            .order_by(ModelSet.type, ModelSet.name)
        )
        result = await session.execute(stmt)
        sets = list(result.scalars().unique().all())
        changed = False
        allow_empty_weights = await cls._get_enable_empty_weights(session)

        for model_set in sets:
            set_has_weights = False
            for entry in model_set.entries:
                has_weights = cls._has_weights(entry.abs_path)
                force_enabled = bool(
                    entry.enabled
                    and not has_weights
                    and entry.disable_reason == cls._FORCE_ENABLED_REASON
                )
                # expose for response serialization
                setattr(entry, "has_weights", has_weights)
                setattr(entry, "force_enabled", force_enabled)
                if has_weights:
                    set_has_weights = True
                    if entry.disable_reason in {
                        cls._SEEDED_WEIGHT_REASON,
                        cls._FORCE_ENABLED_REASON,
                    }:
                        entry.disable_reason = None
                        changed = True
                elif force_enabled:
                    set_has_weights = True
                elif entry.enabled and not force_enabled:
                    if allow_empty_weights:
                        set_has_weights = True
                        continue
                    entry.enabled = False
                    if not entry.disable_reason:
                        entry.disable_reason = cls._SEEDED_WEIGHT_REASON
                    changed = True

            if set_has_weights and model_set.disable_reason == cls._SEEDED_SET_REASON:
                model_set.disable_reason = None
                changed = True

        if changed:
            await session.commit()
            await ProviderManager.refresh(session)

        return sets

    @staticmethod
    async def get_set_by_id(
        session: AsyncSession, set_id: int, *, include_entries: bool = False
    ) -> Optional[ModelSet]:
        stmt = select(ModelSet).where(ModelSet.id == set_id)
        if include_entries:
            stmt = stmt.options(selectinload(ModelSet.entries))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_set_by_name(
        session: AsyncSession, provider_type: str, name: str
    ) -> Optional[ModelSet]:
        stmt = select(ModelSet).where(ModelSet.type == provider_type).where(ModelSet.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_weight_by_id(session: AsyncSession, weight_id: int) -> Optional[ModelEntry]:
        stmt = (
            select(ModelEntry)
            .options(selectinload(ModelEntry.model_set))
            .where(ModelEntry.id == weight_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_weight_by_name(
        session: AsyncSession, set_id: int, name: str
    ) -> Optional[ModelEntry]:
        stmt = (
            select(ModelEntry)
            .options(selectinload(ModelEntry.model_set))
            .where(ModelEntry.set_id == set_id)
            .where(ModelEntry.name == name)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Mutations - Model Sets
    # ------------------------------------------------------------------
    @classmethod
    async def create_model_set(
        cls,
        session: AsyncSession,
        payload: ModelSetCreate,
        actor: str,
    ) -> ModelSet:
        normalized_name = cls._normalize_key(payload.name)
        provider_type = payload.type.lower()
        existing = await cls.get_set_by_name(session, provider_type, normalized_name)
        if existing:
            raise ValueError("set_name_exists")

        abs_path = cls._validate_set_path(payload.abs_path)

        model_set = ModelSet(
            type=provider_type,
            name=normalized_name,
            description=payload.description,
            enabled=True,
            disable_reason=None,
            abs_path=abs_path,
        )

        session.add(model_set)
        await session.commit()
        await session.refresh(model_set)

        write_registry_event("set-created", model_set.name, model_set.name, actor)
        await ProviderManager.refresh(session)
        return model_set

    @classmethod
    async def update_model_set(
        cls,
        session: AsyncSession,
        model_set: ModelSet,
        payload: ModelSetUpdate,
        actor: str,
    ) -> ModelSet:
        updates = payload.model_dump(exclude_unset=True)
        changed = False
        log_action: Optional[str] = None
        log_note: Optional[str] = None

        if "name" in updates:
            new_name = cls._normalize_key(updates["name"])
            if new_name != model_set.name:
                existing = await cls.get_set_by_name(session, model_set.type, new_name)
                if existing and existing.id != model_set.id:
                    raise ValueError("set_name_exists")
                model_set.name = new_name
                changed = True

        for field in ("description",):
            if field in updates:
                setattr(model_set, field, updates[field])
                changed = True

        if "abs_path" in updates:
            model_set.abs_path = cls._validate_set_path(updates["abs_path"])
            changed = True

        disable_reason = updates.pop("disable_reason", None)
        if "enabled" in updates:
            new_state = updates.pop("enabled")
            if new_state and not model_set.enabled:
                model_set.enabled = True
                model_set.disable_reason = None
                changed = True
                log_action = "set-enabled"
            elif new_state is False and model_set.enabled:
                reason = disable_reason or model_set.disable_reason
                if not reason:
                    raise ValueError("disable_reason_required")
                model_set.enabled = False
                model_set.disable_reason = reason
                changed = True
                log_action = "set-disabled"
                log_note = reason
        elif disable_reason:
            model_set.disable_reason = disable_reason
            changed = True

        if not changed:
            return model_set

        await session.commit()
        await session.refresh(model_set)

        # set state impacts availability for downstream caches
        await ProviderManager.refresh(session)

        if log_action:
            write_registry_event(log_action, model_set.name, model_set.name, actor, log_note)

        return model_set

    # ------------------------------------------------------------------
    # Mutations - Model Weights
    # ------------------------------------------------------------------
    @classmethod
    async def create_model_weight(
        cls,
        session: AsyncSession,
        model_set: ModelSet,
        payload: ModelWeightCreate,
        actor: str,
    ) -> ModelEntry:
        normalized_name = cls._normalize_key(payload.name)
        existing = await cls.get_weight_by_name(session, model_set.id, normalized_name)
        if existing:
            raise ValueError("weight_name_exists")

        abs_path = cls._validate_weight_path(payload.abs_path, model_set)

        has_weights = cls._has_weights(abs_path)

        entry = ModelEntry(
            set_id=model_set.id,
            type=model_set.type,
            name=normalized_name,
            description=payload.description,
            checksum=payload.checksum,
            abs_path=abs_path,
            enabled=has_weights,
            disable_reason=None if has_weights else cls._SEEDED_WEIGHT_REASON,
        )

        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        setattr(entry, "has_weights", has_weights)
        setattr(entry, "force_enabled", False)
        await ProviderManager.refresh(session)

        write_registry_event("weight-created", entry.name, entry.name, actor)
        return entry

    @classmethod
    async def update_model_weight(
        cls,
        session: AsyncSession,
        entry: ModelEntry,
        payload: ModelWeightUpdate,
        actor: str,
    ) -> ModelEntry:
        updates = payload.model_dump(exclude_unset=True)
        changed = False
        log_action: Optional[str] = None
        log_note: Optional[str] = None
        allow_empty_weights = await cls._get_enable_empty_weights(session)

        if "name" in updates:
            new_name = cls._normalize_key(updates["name"])
            if new_name != entry.name:
                existing = await cls.get_weight_by_name(session, entry.set_id, new_name)
                if existing and existing.id != entry.id:
                    raise ValueError("weight_name_exists")
                entry.name = new_name
                changed = True

        if "abs_path" in updates:
            entry.abs_path = cls._validate_weight_path(updates["abs_path"], entry.model_set)
            changed = True

        for field in (
            "description",
            "checksum",
        ):
            if field in updates:
                setattr(entry, field, updates[field])
                changed = True

        disable_reason = updates.pop("disable_reason", None)
        if "enabled" in updates:
            new_state = updates.pop("enabled")
            if new_state and not entry.enabled:
                if not cls._has_weights(entry.abs_path):
                    if not allow_empty_weights:
                        raise ValueError("missing_weights")
                    entry.disable_reason = None
                else:
                    entry.disable_reason = None
                entry.enabled = True
                changed = True
                if not log_action:
                    log_action = "weight-enabled"
            elif new_state is False and entry.enabled:
                reason = disable_reason or entry.disable_reason
                if not reason:
                    raise ValueError("disable_reason_required")
                entry.enabled = False
                entry.disable_reason = reason
                changed = True
                log_action = "weight-disabled"
                log_note = reason
        elif disable_reason:
            entry.disable_reason = disable_reason
            changed = True

        if not changed:
            return entry

        await session.commit()
        await session.refresh(entry)
        has_weights = cls._has_weights(entry.abs_path)
        setattr(entry, "has_weights", has_weights)
        setattr(
            entry,
            "force_enabled",
            bool(
                entry.enabled
                and not has_weights
                and entry.disable_reason == cls._FORCE_ENABLED_REASON
            ),
        )
        await ProviderManager.refresh(session)

        if log_action:
            write_registry_event(log_action, entry.name, entry.name, actor, log_note)

        return entry

    @staticmethod
    async def _get_enable_empty_weights(session: AsyncSession) -> bool:
        result = await session.execute(
            select(SystemPreferences.enable_empty_weights).where(SystemPreferences.id == 1)
        )
        value = result.scalar_one_or_none()
        return bool(value)

    @classmethod
    async def delete_model_set(cls, session: AsyncSession, model_set: ModelSet, actor: str) -> None:
        """Delete a model set and all its weights."""

        await session.delete(model_set)
        await session.commit()
        await ProviderManager.refresh(session)
        write_registry_event("set-deleted", model_set.name, model_set.name, actor)

    @classmethod
    async def delete_model_weight(
        cls, session: AsyncSession, entry: ModelEntry, actor: str
    ) -> None:
        """Delete a model weight."""

        await session.delete(entry)
        await session.commit()
        await ProviderManager.refresh(session)
        write_registry_event("weight-deleted", entry.name, entry.name, actor)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_key(key: str) -> str:
        return key.strip().lower()

    @classmethod
    def _validate_set_path(cls, raw_path: str) -> str:
        resolved = cls._resolve_path(raw_path)
        cls._ensure_within_models_root(resolved)
        if resolved.exists() and not resolved.is_dir():
            raise ValueError("invalid_path")
        if not resolved.exists():
            resolved.mkdir(parents=True, exist_ok=True)
        return str(resolved)

    @classmethod
    def _validate_weight_path(cls, raw_path: str, model_set: ModelSet) -> str:
        resolved = cls._resolve_path(raw_path)
        cls._ensure_within_models_root(resolved)
        cls._ensure_within_set_path(resolved, Path(model_set.abs_path))
        if resolved.exists():
            return str(resolved)
        # Path does not exist; create directories as needed
        if resolved.suffix:
            # Looks like a file path; create parent dirs but do not touch the file
            resolved.parent.mkdir(parents=True, exist_ok=True)
        else:
            resolved.mkdir(parents=True, exist_ok=True)
        return str(resolved)

    @classmethod
    def _resolve_path(cls, raw_path: str) -> Path:
        """
        Normalize a user-supplied path so it always resolves within the project root.

        Rules:
        - Absolute paths are allowed only if they live under BACKEND_ROOT/models.
        - Relative paths (including leading "/backend/...") are anchored to BACKEND_ROOT.
        - Prevent traversal outside the project root.
        """
        try:
            normalized = raw_path.strip()
            # Anchor /backend/... or backend/... to the project root
            if normalized.startswith("/backend/"):
                normalized = normalized.removeprefix("/")
            if not Path(normalized).is_absolute():
                candidate = (BACKEND_ROOT / normalized).expanduser()
            else:
                candidate = Path(normalized).expanduser()
        except RuntimeError as exc:  # pragma: no cover - unlikely
            raise ValueError("invalid_path") from exc

        try:
            resolved = candidate.resolve(strict=False)
        except OSError as exc:  # pragma: no cover - permission error etc.
            raise ValueError("invalid_path") from exc
        return cls._coerce_legacy_models_path(resolved)

    @classmethod
    def _has_weights(cls, raw_path: str) -> bool:
        """
        Determine whether a configured path has model weights.

        Rules:
        - Path must live under backend/models (validation mirrors _validate_* helpers).
        - A non-empty directory or a file counts as "has weights".
        """
        try:
            resolved = cls._resolve_path(raw_path)
            cls._ensure_within_models_root(resolved)
        except ValueError:
            return False

        if not resolved.exists():
            return False
        if resolved.is_file():
            return True
        if resolved.is_dir():
            return any(resolved.iterdir())
        return False

    @classmethod
    def _ensure_within_models_root(cls, resolved: Path) -> None:
        models_root = cls._MODELS_ROOT
        try:
            resolved.relative_to(models_root)
        except ValueError as exc:
            raise ValueError("path_outside_models") from exc

    @classmethod
    def _ensure_within_set_path(cls, resolved: Path, set_path: Path) -> None:
        try:
            resolved.relative_to(set_path)
        except ValueError as exc:
            raise ValueError("path_outside_set") from exc

    @classmethod
    def _coerce_legacy_models_path(cls, resolved: Path) -> Path:
        """
        Translate legacy project-level models paths (../models) into the canonical
        backend/models tree so admins can continue editing previously seeded providers.
        """
        legacy_root = cls._LEGACY_MODELS_ROOT
        models_root = cls._MODELS_ROOT
        # If legacy root matches canonical root, nothing to do
        if legacy_root == models_root:
            return resolved
        try:
            relative = resolved.relative_to(legacy_root)
        except ValueError:
            return resolved

        target = (models_root / relative).resolve()
        # Ensure destination directories exist so subsequent validation succeeds
        if resolved.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
        return target
