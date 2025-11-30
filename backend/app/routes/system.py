"""System info routes."""

import asyncio
import os
import signal
import logging

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel

from app.config import PROJECT_ROOT, settings
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


def _require_remote_control(feature: str) -> None:
    """Ensure remote server control is explicitly enabled."""
    if not settings.enable_remote_server_control:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Remote server control ({feature}) is disabled. "
                "Run stop-selenite.ps1/start-selenite.ps1 on the host or set "
                "ENABLE_REMOTE_SERVER_CONTROL=true to opt in."
            ),
        )


def _schedule_sigterm(action: str) -> None:
    """Schedule a SIGTERM after responding so the caller sees success."""

    async def delayed_exit() -> None:
        await asyncio.sleep(1)
        logger.info("Sending SIGTERM for requested %s", action)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(delayed_exit())


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

    _require_remote_control("restart")
    logger.warning("Server restart requested by %s", current_user.username)

    # Schedule the shutdown to happen after we return the response
    _schedule_sigterm("restart")

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

    _require_remote_control("shutdown")
    logger.warning("Server shutdown requested by %s", current_user.username)

    # Schedule the shutdown to happen after we return the response
    _schedule_sigterm("shutdown")

    return ServerActionResponse(
        message="Server shutdown initiated. The server will stop in a moment.", success=True
    )


@router.post("/full-restart", response_model=ServerActionResponse)
async def full_restart_server(current_user: User = Depends(get_current_user)):
    """
    Request a full orchestrated restart (stop + fresh start of all components).

    Implementation detail: creates a sentinel file `restart.flag` that an external
    watchdog script (`scripts/watch-restart.ps1`) monitors. The watchdog will:
      1. Remove the flag
      2. Execute stop-selenite.ps1
      3. Execute start-selenite.ps1

    This avoids executing shell commands directly from inside the API process
    (safer; reduces RCE surface) while still allowing an authenticated admin to
    trigger a controlled restart remotely.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform a full restart",
        )

    _require_remote_control("full restart")

    sentinel_path = PROJECT_ROOT / "restart.flag"
    try:
        with open(sentinel_path, "w", encoding="utf-8") as f:
            f.write(f"requested_by={current_user.username}\n")
        logger.warning(
            "Full orchestrated restart requested by user %s; sentinel created at %s",
            current_user.username,
            sentinel_path,
        )
    except OSError as e:
        logger.error("Failed to create restart sentinel: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create restart sentinel file",
        )

    # Also schedule a graceful termination of current API so the orchestrator does a clean start.
    _schedule_sigterm("full-restart")

    return ServerActionResponse(
        message="Full restart requested. Services will recycle shortly.",
        success=True,
    )
