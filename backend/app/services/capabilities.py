"""Service to report available ASR and diarization options derived from the registry."""

from __future__ import annotations

import logging
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING, Tuple

from app.services.provider_manager import ProviderManager, ProviderRecord
from app.config import BACKEND_ROOT
from app.config import settings

if TYPE_CHECKING:
    from app.models.user_settings import UserSettings

logger = logging.getLogger(__name__)


class ModelResolutionError(Exception):
    """Raised when a requested provider/model combination is invalid."""


# Dependency hints per provider (lightweight importlib spec checks, not full import).
PROVIDER_DEPS: Dict[str, Dict[str, Any]] = {
    # ASR
    "whisper": {"deps": ["whisper"], "requires_gpu": False},
    "faster-whisper": {"deps": ["faster_whisper", "ctranslate2"], "requires_gpu": False},
    "wav2vec2": {"deps": ["transformers", "torch"], "requires_gpu": False},
    "transformers": {"deps": ["transformers", "torch"], "requires_gpu": False},
    "nemo": {"deps": ["nemo_toolkit"], "requires_gpu": False},
    "vosk": {"deps": ["vosk"], "requires_gpu": False},
    "coqui-stt": {"deps": ["stt_native_client", "coqui_stt"], "requires_gpu": False},
    # Diarizer
    "pyannote": {"deps": ["pyannote.audio"], "requires_gpu": False},
    "nemo-diarizer": {"deps": ["nemo_toolkit"], "requires_gpu": False},
    "speechbrain": {"deps": ["speechbrain"], "requires_gpu": False},
    "resemblyzer": {"deps": ["resemblyzer", "webrtcvad"], "requires_gpu": False},
}


def _missing_deps(provider: str) -> List[str]:
    meta = PROVIDER_DEPS.get(provider, {})
    deps = meta.get("deps", [])
    missing = [dep for dep in deps if importlib.util.find_spec(dep) is None]
    return missing


def _resolve_record_path(record: ProviderRecord) -> Path:
    """
    Resolve a record path, allowing relative backend paths (e.g., /backend/models/..)
    to be anchored to the project root. This keeps admin-configured paths portable.
    """
    raw = record.abs_path
    # If already absolute, use as-is
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    # Allow /backend/... style
    normalized = raw.lstrip("/")
    if normalized.startswith("backend"):
        return (BACKEND_ROOT / normalized.removeprefix("backend/")).resolve()
    # Fallback: anchor to model storage root
    return (Path(settings.model_storage_path) / raw).resolve()


def _assess_record(record: ProviderRecord) -> Dict[str, Any]:
    """Evaluate a provider record for availability, notes, and metadata."""

    notes: List[str] = []

    available = True
    requires_gpu = PROVIDER_DEPS.get(record.set_name, {}).get("requires_gpu", False)
    display_name = record.name

    path = _resolve_record_path(record)
    if not record.enabled:
        available = False
        if record.disable_reason:
            notes.append(record.disable_reason)

    allow_empty_weights = ProviderManager.allow_empty_weights()
    if not allow_empty_weights:
        if not path.exists():
            available = False
        elif path.is_dir():
            if not any(path.iterdir()):
                available = False
        else:
            if not path.is_file():
                available = False

    missing = _missing_deps(record.set_name)
    if missing:
        # We assume packages should be installed per requirements; surface as warning but do not hide the model.
        notes.append(
            f"Missing dependency: {', '.join(missing)}. See docs/application_documentation/DEPLOYMENT.md."
        )

    return {
        "available": available,
        "notes": notes,
        "requires_gpu": requires_gpu,
        "display_name": display_name,
    }


def _build_asr_options_from_registry(records: Sequence[ProviderRecord]) -> List[Dict[str, Any]]:
    """Group ASR registry records by provider (model set) and surface their weight names as models."""

    grouped: Dict[str, Dict[str, Any]] = {}
    for record in records:
        assessment = _assess_record(record)
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
        group["models"].append(record.name)
        if assessment["available"]:
            group["available"] = True
        if assessment["notes"]:
            group["notes"].extend(assessment["notes"])

    return list(grouped.values())


def _build_diarizer_options_from_registry(
    records: Sequence[ProviderRecord],
) -> List[Dict[str, Any]]:
    """Return diarizer weights directly; each weight is a selectable backend."""

    options: List[Dict[str, Any]] = []
    for record in records:
        assessment = _assess_record(record)
        options.append(
            {
                "key": record.name,
                "provider": record.set_name,
                "display_name": assessment["display_name"],
                "requires_gpu": assessment["requires_gpu"],
                "available": assessment["available"],
                "notes": assessment["notes"],
            }
        )

    return options


def _collect_asr_models(records: Sequence[ProviderRecord]) -> List[str]:
    """Return enabled & available ASR model weight names."""

    available: List[str] = []
    for record in records:
        assessment = _assess_record(record)
        if assessment["available"]:
            available.append(record.name)
    return available


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
    requested_provider: Optional[str],
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
    asr_records = snapshot["asr"]
    assessments = {(rec.set_name, rec.name): _assess_record(rec) for rec in asr_records}

    def is_available(rec: ProviderRecord) -> bool:
        return assessments[(rec.set_name, rec.name)]["available"]

    grouped: Dict[str, List[ProviderRecord]] = {}
    for rec in asr_records:
        grouped.setdefault(rec.set_name, []).append(rec)

    def first_available(records: List[ProviderRecord]) -> Optional[ProviderRecord]:
        for rec in records:
            if is_available(rec):
                return rec
        return None

    def resolve_from_provider(provider: str, model: Optional[str]) -> ProviderRecord:
        records = grouped.get(provider, [])
        if not records:
            raise ModelResolutionError(f"Provider '{provider}' is not registered.")
        if model:
            entry = next((rec for rec in records if rec.name == model), None)
            if not entry:
                raise ModelResolutionError(
                    f"Model '{model}' is not registered under provider '{provider}'."
                )
            if not is_available(entry):
                raise ModelResolutionError(
                    f"Model '{model}' under provider '{provider}' is disabled or missing weights."
                )
            return entry
        entry = first_available(records)
        if entry:
            return entry
        raise ModelResolutionError(f"Provider '{provider}' has no enabled/available weights.")

    chosen: Optional[ProviderRecord] = None

    if requested_provider:
        chosen = resolve_from_provider(requested_provider, requested_model)
    elif requested_model:
        matches = [rec for rec in asr_records if rec.name == requested_model]
        if not matches:
            raise ModelResolutionError(f"Model '{requested_model}' is not registered.")
        chosen = next((rec for rec in matches if is_available(rec)), None)
        if not chosen:
            raise ModelResolutionError(f"Model '{requested_model}' is disabled or missing weights.")
    else:
        preferred_provider = user_settings.default_asr_provider if user_settings else None
        preferred_model = user_settings.default_model if user_settings else None

        if preferred_provider:
            try:
                chosen = resolve_from_provider(preferred_provider, preferred_model)
            except ModelResolutionError as exc:
                notes.append(str(exc))

        if chosen is None and preferred_model:
            matches = [rec for rec in asr_records if rec.name == preferred_model]
            chosen = next((rec for rec in matches if is_available(rec)), None)
            if chosen is None:
                notes.append(f"Admin default model '{preferred_model}' unavailable; falling back.")

        if chosen is None:
            chosen = first_available(asr_records)

    if chosen is None:
        raise ModelResolutionError(
            "No ASR models available; register and enable one in the admin console."
        )

    model_choice = chosen.name
    provider_choice = chosen.set_name

    diarization_enabled = requested_diarization if requested_diarization is not None else True

    diarizer_choice: Optional[str] = None
    diarizer_provider: Optional[str] = None
    if diarization_enabled:
        capabilities = get_capabilities()
        diarizer_entries = capabilities["diarizers"]
        options = {opt["key"]: opt for opt in diarizer_entries}
        diarizer_choice = _select_available_diarizer(requested_diarizer, options, notes)
        if diarizer_choice is None:
            diarization_enabled = False
            notes.append("No diarizer backends available; disabling speaker labels for this job")
        else:
            diarizer_provider = options.get(diarizer_choice, {}).get("provider")

    return {
        "model": model_choice,
        "provider": provider_choice,
        "diarizer": diarizer_choice,
        "diarizer_provider": diarizer_provider,
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
