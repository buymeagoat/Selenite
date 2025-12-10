"""Business logic for the model registry."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import BACKEND_ROOT
from app.models.model_provider import ModelEntry, ModelSet
from app.schemas.model_registry import (
    ModelEntryCreate,
    ModelEntryUpdate,
    ModelSetCreate,
    ModelSetUpdate,
)
from app.services.provider_manager import ProviderManager
from app.utils.memorialization import write_registry_event


class ModelRegistryService:
    """Service helpers for CRUD operations on model sets and entries."""

    _MODELS_ROOT = (BACKEND_ROOT / "models").resolve()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    @staticmethod
    async def list_model_sets(session: AsyncSession) -> list[ModelSet]:
        stmt = (
            select(ModelSet)
            .options(selectinload(ModelSet.entries))
            .order_by(ModelSet.type, ModelSet.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

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
    async def get_entry_by_id(session: AsyncSession, entry_id: int) -> Optional[ModelEntry]:
        stmt = (
            select(ModelEntry)
            .options(selectinload(ModelEntry.model_set))
            .where(ModelEntry.id == entry_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_entry_by_name(
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
    # Mutations - Model Entries
    # ------------------------------------------------------------------
    @classmethod
    async def create_model_entry(
        cls,
        session: AsyncSession,
        model_set: ModelSet,
        payload: ModelEntryCreate,
        actor: str,
    ) -> ModelEntry:
        normalized_name = cls._normalize_key(payload.name)
        existing = await cls.get_entry_by_name(session, model_set.id, normalized_name)
        if existing:
            raise ValueError("entry_name_exists")

        abs_path = cls._validate_entry_path(payload.abs_path, model_set)

        entry = ModelEntry(
            set_id=model_set.id,
            type=model_set.type,
            name=normalized_name,
            description=payload.description,
            checksum=payload.checksum,
            abs_path=abs_path,
            enabled=True,
            disable_reason=None,
        )

        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        await ProviderManager.refresh(session)

        write_registry_event("entry-created", entry.name, entry.name, actor)
        return entry

    @classmethod
    async def update_model_entry(
        cls,
        session: AsyncSession,
        entry: ModelEntry,
        payload: ModelEntryUpdate,
        actor: str,
    ) -> ModelEntry:
        updates = payload.model_dump(exclude_unset=True)
        changed = False
        log_action: Optional[str] = None
        log_note: Optional[str] = None

        if "name" in updates:
            new_name = cls._normalize_key(updates["name"])
            if new_name != entry.name:
                existing = await cls.get_entry_by_name(session, entry.set_id, new_name)
                if existing and existing.id != entry.id:
                    raise ValueError("entry_name_exists")
                entry.name = new_name
                changed = True

        if "abs_path" in updates:
            entry.abs_path = cls._validate_entry_path(updates["abs_path"], entry.model_set)
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
                entry.enabled = True
                entry.disable_reason = None
                changed = True
                log_action = "entry-enabled"
            elif new_state is False and entry.enabled:
                reason = disable_reason or entry.disable_reason
                if not reason:
                    raise ValueError("disable_reason_required")
                entry.enabled = False
                entry.disable_reason = reason
                changed = True
                log_action = "entry-disabled"
                log_note = reason
        elif disable_reason:
            entry.disable_reason = disable_reason
            changed = True

        if not changed:
            return entry

        await session.commit()
        await session.refresh(entry)
        await ProviderManager.refresh(session)

        if log_action:
            write_registry_event(log_action, entry.name, entry.name, actor, log_note)

        return entry

    @classmethod
    async def delete_model_set(cls, session: AsyncSession, model_set: ModelSet, actor: str) -> None:
        """Delete a model set and all its entries."""

        await session.delete(model_set)
        await session.commit()
        await ProviderManager.refresh(session)
        write_registry_event("set-deleted", model_set.name, model_set.name, actor)

    @classmethod
    async def delete_model_entry(cls, session: AsyncSession, entry: ModelEntry, actor: str) -> None:
        """Delete a model entry."""

        await session.delete(entry)
        await session.commit()
        await ProviderManager.refresh(session)
        write_registry_event("entry-deleted", entry.name, entry.name, actor)

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
    def _validate_entry_path(cls, raw_path: str, model_set: ModelSet) -> str:
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
        try:
            normalized = raw_path.strip()
            # Allow UI paths expressed as /backend/... by anchoring to BACKEND_ROOT
            if normalized.startswith("/backend/"):
                normalized = str(BACKEND_ROOT / normalized.removeprefix("/backend/"))
            candidate = Path(normalized).expanduser()
        except RuntimeError as exc:  # pragma: no cover - unlikely
            raise ValueError("invalid_path") from exc

        if not candidate.is_absolute():
            raise ValueError("path_must_be_absolute")

        try:
            resolved = candidate.resolve(strict=False)
        except OSError as exc:  # pragma: no cover - permission error etc.
            raise ValueError("invalid_path") from exc
        return resolved

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
