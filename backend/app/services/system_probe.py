"""System probe helpers for reporting host capabilities."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - tests stub psutil if absent
    psutil = None  # type: ignore[assignment]
from sqlalchemy.engine import make_url

from app.config import BACKEND_ROOT, settings

ProbePayload = Dict[str, Any]


def _resolve_sqlite_path() -> Optional[Path]:
    """Resolve the on-disk SQLite database path, if configured."""
    try:
        db_url = make_url(settings.database_url)
    except Exception:
        return None

    if not db_url.get_backend_name().startswith("sqlite"):
        return None

    db_path = db_url.database
    if not db_path:
        return None

    path = Path(db_path)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


def _gather_disk_usage(path: Path) -> Dict[str, Any]:
    """Return disk usage statistics for the provided path."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Ignore directory creation issues; fall back to parent
        pass

    try:
        usage = shutil.disk_usage(path)
        return {
            "path": str(path),
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        return {"path": str(path), "total_gb": None, "used_gb": None, "free_gb": None}


def _collect_os_info() -> Dict[str, Any]:
    uname = platform.uname()
    return {
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
    }


def _collect_cpu_info() -> Dict[str, Any]:
    freq = psutil.cpu_freq() if psutil else None
    uname = platform.uname()
    cores_physical = psutil.cpu_count(logical=False) if psutil else os.cpu_count()
    cores_logical = psutil.cpu_count(logical=True) if psutil else os.cpu_count()
    return {
        "model": uname.processor or platform.processor() or None,
        "architecture": platform.machine(),
        "cores_physical": cores_physical,
        "cores_logical": cores_logical,
        "max_frequency_mhz": freq.max if freq else None,
    }


def _collect_memory_info() -> Dict[str, Any]:
    if not psutil:
        return {"total_gb": None, "available_gb": None}
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
    }


def _collect_gpu_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "has_gpu": False,
        "api": None,
        "devices": [],
        "driver": None,
    }
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            devices: List[Dict[str, Any]] = []
            for idx in range(device_count):
                props = torch.cuda.get_device_properties(idx)
                devices.append(
                    {
                        "name": props.name,
                        "memory_gb": round(props.total_memory / (1024**3), 2),
                        "multi_processor_count": props.multi_processor_count,
                    }
                )
            info.update(
                {
                    "has_gpu": True,
                    "api": "cuda",
                    "devices": devices,
                    "driver": torch.version.cuda,
                }
            )
        elif getattr(torch.version, "hip", None):
            # ROCm build detected; attempt to gather device info
            try:
                device_count = torch.cuda.device_count()
            except Exception:
                device_count = 0
            devices: List[Dict[str, Any]] = []
            for idx in range(device_count):
                try:
                    props = torch.cuda.get_device_properties(idx)
                except Exception:
                    continue
                devices.append(
                    {
                        "name": props.name,
                        "memory_gb": round(props.total_memory / (1024**3), 2),
                        "multi_processor_count": props.multi_processor_count,
                    }
                )
            info.update(
                {
                    "has_gpu": bool(devices),
                    "api": "rocm" if devices else None,
                    "devices": devices,
                    "driver": torch.version.hip,
                }
            )
    except Exception:
        # Torch not available or GPU query failed; leave defaults
        pass
    return info


def _collect_network_info() -> Dict[str, Any]:
    interfaces = []
    hostname = socket.gethostname()
    if not psutil:
        return {"hostname": hostname, "interfaces": interfaces}
    for iface_name, addresses in psutil.net_if_addrs().items():
        ipv4 = []
        for addr in addresses:
            if addr.family == socket.AF_INET:
                ipv4.append(addr.address)
        if ipv4:
            interfaces.append({"name": iface_name, "ipv4": ipv4})
    return {"hostname": hostname, "interfaces": interfaces}


def _collect_runtime_info() -> Dict[str, Any]:
    python_version = platform.python_version()
    node_version = None
    try:
        completed = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        node_version = completed.stdout.strip()
    except Exception:
        node_version = None
    return {
        "python": python_version,
        "node": node_version,
    }


def _detect_containerization() -> Dict[str, Any]:
    indicators: List[str] = []
    if Path("/.dockerenv").exists():
        indicators.append("dockerenv")
    try:
        with open("/proc/1/cgroup", "r", encoding="utf-8") as handle:
            cgroup_data = handle.read()
        if "docker" in cgroup_data or "kubepods" in cgroup_data:
            indicators.append("cgroup")
    except Exception:
        # Windows or environments without /proc
        pass
    if os.environ.get("CONTAINER") or os.environ.get("RUNNING_IN_CONTAINER"):
        indicators.append("env")
    return {
        "is_container": bool(indicators),
        "indicators": indicators,
    }


def _collect_storage_info() -> Dict[str, Any]:
    db_path = _resolve_sqlite_path()
    media_path = Path(settings.media_storage_path)
    transcript_path = Path(settings.transcript_storage_path)
    project_root = BACKEND_ROOT.parent
    return {
        "database": _gather_disk_usage(db_path) if db_path else None,
        "media": _gather_disk_usage(media_path),
        "transcripts": _gather_disk_usage(transcript_path),
        "project": _gather_disk_usage(project_root),
    }


def _recommend_profile(memory_info: Dict[str, Any], gpu_info: Dict[str, Any]) -> Dict[str, Any]:
    """Return a simple recommendation for ASR/diarization defaults."""
    vram_gb = 0.0
    if gpu_info.get("devices"):
        vram_gb = max(device.get("memory_gb", 0) or 0 for device in gpu_info["devices"])

    total_ram = memory_info.get("total_gb") or 0
    asr_model = "medium"
    diarizer = "vad"
    reason = []

    if gpu_info.get("api") == "cuda" and vram_gb >= 16:
        asr_model = "large-v3"
        diarizer = "pyannote"
        reason.append(">=16GB VRAM GPU detected")
    elif gpu_info.get("api") in {"cuda", "rocm"} and vram_gb >= 8:
        asr_model = "medium"
        diarizer = "whisperx"
        reason.append(">=8GB VRAM GPU detected")
    elif total_ram >= 16:
        asr_model = "small"
        diarizer = "vad"
        reason.append(">=16GB system RAM without GPU")
    else:
        asr_model = "base"
        diarizer = "vad"
        reason.append("Limited memory; prefer lightweight defaults")

    return {
        "suggested_asr_model": asr_model,
        "suggested_diarization": diarizer,
        "basis": reason,
    }


def build_probe_payload() -> ProbePayload:
    """Collect a snapshot of the host system."""
    os_info = _collect_os_info()
    cpu_info = _collect_cpu_info()
    memory_info = _collect_memory_info()
    gpu_info = _collect_gpu_info()
    storage_info = _collect_storage_info()
    network_info = _collect_network_info()
    runtime_info = _collect_runtime_info()
    container_info = _detect_containerization()
    recommendation = _recommend_profile(memory_info, gpu_info)

    return {
        "detected_at": datetime.now(timezone.utc),
        "os": os_info,
        "cpu": cpu_info,
        "memory": memory_info,
        "gpu": gpu_info,
        "storage": storage_info,
        "network": network_info,
        "runtime": runtime_info,
        "container": container_info,
        "recommendation": recommendation,
    }


class SystemProbeService:
    """Simple in-memory cache for system probe results."""

    _cache: Optional[ProbePayload] = None

    @classmethod
    def get_cached_probe(cls) -> ProbePayload:
        if cls._cache is None:
            cls._cache = build_probe_payload()
        return cls._cache

    @classmethod
    def refresh_probe(cls) -> ProbePayload:
        cls._cache = build_probe_payload()
        return cls._cache
