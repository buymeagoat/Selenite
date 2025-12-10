"""Helpers for writing memorialization entries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

_MEMORIAL_ROOT = PROJECT_ROOT / "docs" / "memorialization"
_REGISTRY_LOG = _MEMORIAL_ROOT / "model-registry.log"


def write_registry_event(
    action: str, provider_key: str, display_name: str, actor: str, note: Optional[str] = None
) -> None:
    """Append a provider registry action to the memorialization log."""

    timestamp = datetime.now(tz=timezone.utc).isoformat()
    entry = f"[{timestamp}] action={action} provider={provider_key} display={display_name} actor={actor}"
    if note:
        entry = f"{entry} note={note}"

    try:
        _MEMORIAL_ROOT.mkdir(parents=True, exist_ok=True)
        with _REGISTRY_LOG.open("a", encoding="utf-8") as handle:
            handle.write(entry + "\n")
    except OSError as exc:  # pragma: no cover - filesystem issue
        logger.warning("Failed to write memorialization entry: %s", exc)
