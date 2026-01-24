"""System info routes."""

import asyncio
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import PROJECT_ROOT
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.system import SystemProbeResponse
from app.schemas.capabilities import CapabilityResponse
from app.services.system_probe import SystemProbeService
from app.services.capabilities import get_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SystemProbeResponse)
async def get_system_info(current_user: User = Depends(get_current_user)):
    """Return the most recent system probe."""
    return SystemProbeService.get_cached_probe()


@router.post("/info/detect", response_model=SystemProbeResponse, status_code=status.HTTP_200_OK)
async def refresh_system_info(current_user: User = Depends(get_current_user)):
    """Trigger a fresh system probe and return it."""
    return SystemProbeService.refresh_probe()


@router.get("/availability", response_model=CapabilityResponse)
async def get_system_capabilities(current_user: User = Depends(get_current_user)):
    """Report available ASR and diarization options."""
    return get_capabilities()


class ServerActionResponse(BaseModel):
    """Response for server control actions."""

    message: str
    success: bool


class SystemLogItem(BaseModel):
    name: str
    size_bytes: int
    modified_at: datetime


def _schedule_script(action: str, script_name: str) -> None:
    """Schedule a PowerShell script to run after returning a response."""
    script_path = PROJECT_ROOT / "scripts" / script_name
    shell_exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    async def delayed_run() -> None:
        await asyncio.sleep(1)
        if not script_path.exists():
            logger.error("Restart script missing for %s: %s", action, script_path)
            return
        try:
            subprocess.Popen(
                [
                    shell_exe,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                creationflags=creation_flags,
            )
            logger.info("Scheduled %s via %s", action, script_path)
        except Exception as exc:
            logger.error("Failed to launch %s script (%s): %s", action, script_path, exc)

    asyncio.create_task(delayed_run())


@router.post("/restart", response_model=ServerActionResponse)
async def restart_server(current_user: User = Depends(get_current_user)):
    """
    Restart the server process.

    This will send a SIGTERM signal to gracefully shutdown the current process.
    The process manager (like systemd, docker, or the start script) should
    automatically restart it.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can restart the server",
        )

    logger.warning("Server restart requested by %s", current_user.username)

    _schedule_script("restart", "restart-selenite.ps1")

    return ServerActionResponse(
        message="Server restart initiated. The server will restart in a moment.", success=True
    )


@router.post("/shutdown", response_model=ServerActionResponse)
async def shutdown_server(current_user: User = Depends(get_current_user)):
    """
    Shutdown the server process.

    This will send a SIGTERM signal to gracefully shutdown the server.
    All active transcription jobs will be interrupted.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can shutdown the server",
        )

    logger.warning("Server shutdown requested by %s", current_user.username)

    _schedule_script("shutdown", "stop-selenite.ps1")

    return ServerActionResponse(
        message="Server shutdown initiated. The server will stop in a moment.", success=True
    )


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access system logs",
        )


def _logs_root() -> Path:
    return PROJECT_ROOT / "logs"


@router.get("/logs", response_model=list[SystemLogItem])
async def list_system_logs(current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    logs_dir = _logs_root()
    if not logs_dir.exists():
        return []
    items: list[SystemLogItem] = []
    for entry in logs_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.endswith(".log"):
            continue
        stat = entry.stat()
        items.append(
            SystemLogItem(
                name=entry.name,
                size_bytes=stat.st_size,
                modified_at=datetime.utcfromtimestamp(stat.st_mtime),
            )
        )
    items.sort(key=lambda item: item.modified_at, reverse=True)
    return items


@router.get("/logs/{log_name}")
async def download_system_log(log_name: str, current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    if "/" in log_name or "\\" in log_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid log name")
    logs_dir = _logs_root()
    log_path = logs_dir / log_name
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log file not found")
    return FileResponse(log_path, media_type="text/plain", filename=log_name)
