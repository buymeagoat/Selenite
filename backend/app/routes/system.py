"""System info routes."""

from fastapi import APIRouter, Depends, status

from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.system import SystemProbeResponse
from app.schemas.capabilities import CapabilityResponse
from app.services.system_probe import SystemProbeService
from app.services.capabilities import get_capabilities

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
