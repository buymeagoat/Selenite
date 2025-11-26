"""Service to report available ASR and diarization options."""

from __future__ import annotations

import importlib.util
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

from app.config import settings
from app.services.system_probe import SystemProbeService

if TYPE_CHECKING:
    from app.models.user_settings import UserSettings


VALID_ASR_MODELS = ["tiny", "base", "small", "medium", "large", "large-v3"]
DIARIZER_PRIORITY = ["whisperx", "pyannote", "vad"]


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _max_gpu_memory_gb(probe: Dict[str, Any]) -> float:
    devices = probe.get("gpu", {}).get("devices") or []
    max_mem = 0.0
    for device in devices:
        mem = device.get("memory_gb") or 0
        if mem > max_mem:
            max_mem = mem
    return max_mem


def _build_diarizer_options() -> List[Dict[str, Any]]:
    probe = SystemProbeService.get_cached_probe()
    gpu_info = probe.get("gpu", {})
    has_gpu = bool(gpu_info.get("has_gpu"))
    max_mem = _max_gpu_memory_gb(probe)

    options: List[Dict[str, Any]] = []

    def entry(
        key: str,
        display: str,
        requires_gpu: bool,
        module_name: str | None,
        notes: List[str],
        min_vram: float = 0.0,
    ) -> Dict[str, Any]:
        available = True
        reasons: List[str] = []
        if requires_gpu and not has_gpu:
            available = False
            reasons.append("GPU required")
        if requires_gpu and min_vram and max_mem < min_vram:
            available = False
            reasons.append(f"Requires >= {min_vram:.0f}GB VRAM")
        if module_name and not _has_module(module_name):
            available = False
            reasons.append(f"{module_name} not installed")
        reasons.extend(notes)
        return {
            "key": key,
            "display_name": display,
            "requires_gpu": requires_gpu,
            "available": available,
            "notes": reasons,
        }

    options.append(entry("whisperx", "WhisperX Diarization", True, "whisperx", [], min_vram=8.0))
    options.append(
        entry(
            "pyannote", "Pyannote (speaker diarization)", True, "pyannote.audio", [], min_vram=12.0
        )
    )
    options.append(entry("vad", "VAD + clustering", False, None, []))
    return options


def _build_asr_options() -> List[Dict[str, Any]]:
    models = ["tiny", "base", "small", "medium", "large-v3"]
    return [
        {
            "provider": "whisper",
            "display_name": "OpenAI Whisper",
            "available": True,
            "models": models,
            "notes": [],
        }
    ]


def get_capabilities() -> Dict[str, Any]:
    """Return ASR and diarizer availability metadata."""
    return {
        "asr": _build_asr_options(),
        "diarizers": _build_diarizer_options(),
    }


def _resolve_model_choice(
    requested: Optional[str], user_settings: Optional["UserSettings"], notes: List[str]
) -> str:
    default_model = (
        user_settings.default_model if user_settings else settings.default_whisper_model
    ) or "medium"
    candidate = requested or default_model
    if candidate not in VALID_ASR_MODELS:
        if requested:
            notes.append(f"Requested model '{requested}' is invalid; falling back to defaults")
        candidate = default_model if default_model in VALID_ASR_MODELS else "medium"
    return candidate


def _select_available_diarizer(
    preferred: Optional[str], options: Dict[str, Dict[str, Any]], notes: List[str]
) -> Optional[str]:
    if preferred:
        opt = options.get(preferred)
        if opt and opt["available"]:
            return preferred
        notes.append(f"Diarizer '{preferred}' unavailable; checking fallbacks")
    for key in DIARIZER_PRIORITY:
        opt = options.get(key)
        if opt and opt["available"]:
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
    Resolve job model/diarization choices with fallback to admin defaults and capability checks.

    Returns dict with keys: model, diarizer (or None), diarization_enabled (bool), notes (List[str]).
    """
    notes: List[str] = []
    model_choice = _resolve_model_choice(requested_model, user_settings, notes)

    allow_override = bool(user_settings and user_settings.allow_job_overrides)
    diarization_enabled = bool(user_settings and user_settings.diarization_enabled)
    if requested_diarization is not None:
        if allow_override:
            diarization_enabled = requested_diarization
        else:
            notes.append("Per-job diarization toggle ignored (admin disabled overrides)")

    diarizer_choice: Optional[str] = None
    if diarization_enabled:
        preferred = (
            requested_diarizer
            if (allow_override and requested_diarizer)
            else (user_settings.default_diarizer if user_settings else "vad")
        )
        capabilities = get_capabilities()
        options = {opt["key"]: opt for opt in capabilities["diarizers"]}
        diarizer_choice = _select_available_diarizer(preferred, options, notes)
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
    Build the runtime Whisper model preference order.

    Priority:
    1. Job-specific model (if valid)
    2. Admin default (if set/valid)
    3. Global default from settings
    4. Built-in safe fallback ("medium")
    """

    candidates: List[str] = []

    def push(candidate: Optional[str]) -> None:
        if not candidate:
            return
        if candidate not in VALID_ASR_MODELS:
            return
        if candidate not in candidates:
            candidates.append(candidate)

    push(current_model)
    if user_settings:
        push(user_settings.default_model)
    push(settings.default_whisper_model)
    push("medium")
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

    admin_enabled = bool(user_settings and user_settings.diarization_enabled)
    if admin_enabled:
        push("admin", user_settings.default_diarizer)

    for fallback_key in DIARIZER_PRIORITY:
        push("fallback", fallback_key)

    for source, key in order:
        option = options.get(key)
        if option and option["available"]:
            if source != "job":
                if source == "admin":
                    notes.append(
                        f"Job diarizer '{requested_diarizer}' unavailable; using admin default '{key}'"
                    )
                else:
                    notes.append(
                        f"Job diarizer '{requested_diarizer}' unavailable; falling back to '{key}'"
                    )
            return {"diarizer": key, "diarization_enabled": True, "notes": notes}
        if source == "job":
            notes.append(f"Diarizer '{key}' unavailable at runtime")

    notes.append("No diarizer backends available; disabling speaker labels")
    return {"diarizer": None, "diarization_enabled": False, "notes": notes}
