"""In-memory cache of registered ASR and diarizer providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import RLock
from typing import Dict, List, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model_provider import ModelEntry, ModelSet

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    """Represents a model entry needed for capability lookups."""

    set_id: int
    entry_id: int
    set_name: str
    name: str
    provider_type: str  # "asr" | "diarizer"
    abs_path: str
    enabled: bool
    disable_reason: str | None
    checksum: str | None


ProviderSnapshot = Dict[str, List[ProviderRecord]]


class ProviderManager:
    """Caches provider records so availability checks stay fast."""

    _lock: RLock = RLock()
    _snapshot: ProviderSnapshot = {"asr": [], "diarizers": []}
    _initialized: bool = False

    @classmethod
    async def refresh(cls, session: AsyncSession) -> None:
        """Reload provider records from the database into the cache."""

        result = await session.execute(
            select(ModelEntry)
            .options(selectinload(ModelEntry.model_set))
            .join(ModelSet)
            .order_by(ModelSet.type, ModelSet.name, ModelEntry.name)
        )
        entries = list(result.scalars().unique().all())
        records = cls._serialize(entries)
        with cls._lock:
            cls._snapshot = records
            cls._initialized = True
        logger.info(
            "Provider catalog refreshed (asr=%s, diarizers=%s)",
            len(records["asr"]),
            len(records["diarizers"]),
        )

    @classmethod
    def get_snapshot(cls) -> ProviderSnapshot:
        """Return the latest cached providers grouped by type."""

        with cls._lock:
            return {
                "asr": list(cls._snapshot["asr"]),
                "diarizers": list(cls._snapshot["diarizers"]),
            }

    @classmethod
    def is_initialized(cls) -> bool:
        """Whether the cache has been populated from the database."""

        with cls._lock:
            return cls._initialized

    @classmethod
    def _serialize(cls, entries: Sequence[ModelEntry]) -> ProviderSnapshot:
        asr_records: List[ProviderRecord] = []
        diarizer_records: List[ProviderRecord] = []

        for entry in entries:
            model_set = entry.model_set
            if not model_set:
                logger.warning("Skipping model entry %s without parent set", entry.name)
                continue

            combined_enabled = bool(model_set.enabled and entry.enabled)
            disable_reason = entry.disable_reason or model_set.disable_reason

            record = ProviderRecord(
                set_id=model_set.id,
                entry_id=entry.id,
                set_name=model_set.name,
                name=entry.name,
                provider_type=model_set.type,
                abs_path=entry.abs_path,
                enabled=combined_enabled,
                disable_reason=disable_reason,
                checksum=entry.checksum,
            )

            if model_set.type == "asr":
                asr_records.append(record)
            else:
                diarizer_records.append(record)

        return {"asr": asr_records, "diarizers": diarizer_records}


__all__ = ["ProviderManager", "ProviderRecord"]
