"""Service to report available ASR and diarization options derived from the registry."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING, Tuple

from app.services.provider_manager import ProviderManager, ProviderRecord

if TYPE_CHECKING:
    from app.models.user_settings import UserSettings

logger = logging.getLogger(__name__)


def _build_asr_options_from_registry(records: Sequence[ProviderRecord]) -> List[Dict[str, Any]]:
    """Group ASR registry records by provider (model set) and surface their entry names as models."""

    if not records:
        logger.warning("ASR registry empty; availability returns no providers")
        return []

    grouped: Dict[str, Dict[str, Any]] = {}
    for record in records:
        group = grouped.setdefault(
            record.set_name,
            {
                "provider": record.set_name,
                "display_name": record.set_name,
                "models": [],
                "available": False,
                "notes": [],
            },
        )
        if record.enabled:
            group["available"] = True
            group["models"].append(record.name)
        elif record.disable_reason:
            group["notes"].append(record.disable_reason)

    return list(grouped.values())


def _build_diarizer_options_from_registry(
    records: Sequence[ProviderRecord],
) -> List[Dict[str, Any]]:
    """Return diarizer entries directly; each entry is a selectable backend."""

    if not records:
        logger.warning("Diarizer registry empty; availability returns no providers")
        return []

    options: List[Dict[str, Any]] = []
    for record in records:
        notes: List[str] = []
        if not record.enabled and record.disable_reason:
            notes.append(record.disable_reason)
        options.append(
            {
                "key": record.name,
                "display_name": record.name,
                "requires_gpu": False,
                "available": record.enabled,
                "notes": notes,
            }
        )

    return options


def _collect_asr_models(records: Sequence[ProviderRecord]) -> List[str]:
    """Return enabled ASR model entry names."""

    return [record.name for record in records if record.enabled]


def get_capabilities() -> Dict[str, Any]:
    """Return ASR and diarizer availability metadata."""

    snapshot = ProviderManager.get_snapshot()
    return {
        "asr": _build_asr_options_from_registry(snapshot["asr"]),
        "diarizers": _build_diarizer_options_from_registry(snapshot["diarizers"]),
    }


def _resolve_model_choice(
    requested: Optional[str],
    admin_default: Optional[str],
    valid_models: Sequence[str],
    notes: List[str],
) -> Optional[str]:
    """Pick the requested model when valid; otherwise fall back to the first available."""

    if not valid_models:
        return None
    if requested:
        if requested in valid_models:
            return requested
        notes.append(f"Requested model '{requested}' unavailable; using defaults instead")
    if admin_default:
        if admin_default in valid_models:
            return admin_default
        notes.append(
            f"Admin default model '{admin_default}' unavailable; falling back to first available"
        )
    return valid_models[0]


def _select_available_diarizer(
    preferred: Optional[str],
    options: Dict[str, Dict[str, Any]],
    notes: List[str],
) -> Optional[str]:
    """Pick a diarizer from the available options with a simple fallback order."""

    if preferred:
        opt = options.get(preferred)
        if opt and opt["available"]:
            return preferred
        if preferred:
            notes.append(f"Diarizer '{preferred}' unavailable; checking fallbacks")

    for key, opt in options.items():
        if opt.get("available"):
            return key

    return None


def resolve_job_preferences(
    *,
    requested_model: Optional[str],
    requested_diarizer: Optional[str],
    requested_diarization: Optional[bool],
    user_settings: Optional["UserSettings"],
) -> Dict[str, Any]:
    """
    Resolve job model/diarization choices with fallback to registry availability.

    Returns dict with keys: model, diarizer (or None), diarization_enabled (bool), notes (List[str]).
    """

    notes: List[str] = []
    snapshot = ProviderManager.get_snapshot()
    valid_models = _collect_asr_models(snapshot["asr"])

    if not valid_models:
        notes.append("No ASR models available; register and enable one in the admin console.")
        return {"model": None, "diarizer": None, "diarization_enabled": False, "notes": notes}

    admin_default_model = user_settings.default_model if user_settings else None
    model_choice = _resolve_model_choice(requested_model, admin_default_model, valid_models, notes)

    diarization_enabled = requested_diarization if requested_diarization is not None else True

    diarizer_choice: Optional[str] = None
    if diarization_enabled:
        capabilities = get_capabilities()
        diarizer_entries = capabilities["diarizers"]
        options = {opt["key"]: opt for opt in diarizer_entries}
        diarizer_choice = _select_available_diarizer(requested_diarizer, options, notes)
        if diarizer_choice is None:
            diarization_enabled = False
            notes.append("No diarizer backends available; disabling speaker labels for this job")

    return {
        "model": model_choice,
        "diarizer": diarizer_choice,
        "diarization_enabled": diarization_enabled,
        "notes": notes,
    }


def get_asr_candidate_order(
    current_model: Optional[str], user_settings: Optional["UserSettings"]
) -> List[str]:
    """
    Build the runtime ASR model preference order using registry data.

    Priority:
    1. Job-specific model (if valid)
    2. Admin default (if set/valid)
    3. Any remaining enabled models
    """

    snapshot = ProviderManager.get_snapshot()
    valid_models = _collect_asr_models(snapshot["asr"])
    candidate_set = set(valid_models)

    candidates: List[str] = []

    def push(candidate: Optional[str]) -> None:
        if not candidate:
            return
        if candidate not in candidate_set:
            return
        if candidate not in candidates:
            candidates.append(candidate)

    push(current_model)
    if user_settings:
        push(user_settings.default_model)
    for model in valid_models:
        push(model)

    return candidates


def enforce_runtime_diarizer(
    *,
    requested_diarizer: Optional[str],
    diarization_requested: bool,
    user_settings: Optional["UserSettings"],
) -> Dict[str, Any]:
    """
    Ensure a viable diarizer is selected at runtime with graceful fallback.

    Returns: {"diarizer": Optional[str], "diarization_enabled": bool, "notes": List[str]}
    """

    notes: List[str] = []
    if not diarization_requested:
        return {"diarizer": None, "diarization_enabled": False, "notes": notes}

    capabilities = get_capabilities()
    options = {opt["key"]: opt for opt in capabilities["diarizers"]}

    order: List[Tuple[str, str]] = []
    seen: set[str] = set()

    def push(source: str, key: Optional[str]) -> None:
        if not key or key in seen:
            return
        seen.add(key)
        order.append((source, key))

    push("job", requested_diarizer)

    admin_default = user_settings.default_diarizer if user_settings else None
    push("admin", admin_default)

    for fallback_key in options:
        push("fallback", fallback_key)

    for source, key in order:
        option = options.get(key)
        if option and option["available"]:
            if source != "job" and requested_diarizer:
                if source == "admin":
                    notes.append(
                        f"Job diarizer '{requested_diarizer}' unavailable; using admin default '{key}'"
                    )
                else:
                    notes.append(
                        f"Job diarizer '{requested_diarizer}' unavailable; falling back to '{key}'"
                    )
            return {"diarizer": key, "diarization_enabled": True, "notes": notes}
        if source == "job" and key:
            notes.append(f"Diarizer '{key}' unavailable at runtime")

    notes.append("No diarizer backends available; disabling speaker labels")
    return {"diarizer": None, "diarization_enabled": False, "notes": notes}
