"""
Diagnostics endpoints for troubleshooting client-side issues.
"""

import logging
from datetime import datetime
from typing import Any, Optional, Dict

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel

from app.models.user import User
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class ClientLog(BaseModel):
    """Client-side log entry"""

    level: str  # 'error', 'warn', 'info', 'debug'
    message: str
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    user_agent: Optional[str] = None


class ClientError(BaseModel):
    """Client-side error report"""

    error_message: str
    error_name: Optional[str] = None
    error_stack: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


SENSITIVE_KEYS = {"authorization", "cookie", "x-api-key", "proxy-authorization", "set-cookie"}


def _scrub_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Remove obvious secrets from the context payload."""
    if not context:
        return {}
    sanitized: Dict[str, Any] = {}
    for key, value in context.items():
        if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "[scrubbed]"
        else:
            sanitized[key] = value
    return sanitized


@router.post("/log")
async def log_client_event(
    log: ClientLog,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Receive and log client-side events for debugging.

    This allows the frontend to send diagnostic information
    to the backend where it can be centrally logged.
    """
    log_level = getattr(logging, log.level.upper(), logging.INFO)

    log_data = {
        "source": "client",
        "client_message": log.message,
        "context": _scrub_context(log.context),
        "timestamp": log.timestamp or datetime.utcnow().isoformat(),
        "user_agent": log.user_agent or request.headers.get("user-agent"),
        "client_ip": request.client.host if request.client else None,
        "user_id": current_user.id,
        "username": current_user.username,
    }

    logger.log(log_level, f"[CLIENT LOG] {log.message}", extra=log_data)

    return {"status": "logged"}


@router.post("/error")
async def log_client_error(
    error: ClientError,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Receive and log client-side errors for debugging.

    This captures uncaught errors, network failures, and other
    issues that occur in the browser.
    """
    error_data = {
        "source": "client_error",
        "error_name": error.error_name,
        "error_message": error.error_message,
        "error_stack": error.error_stack,
        "url": error.url,
        "context": _scrub_context(error.context),
        "timestamp": error.timestamp or datetime.utcnow().isoformat(),
        "user_agent": error.user_agent or request.headers.get("user-agent"),
        "client_ip": request.client.host if request.client else None,
        "user_id": current_user.id,
        "username": current_user.username,
    }

    logger.error(f"[CLIENT ERROR] {error.error_message}", extra=error_data)

    return {"status": "logged", "error_id": f"err_{datetime.utcnow().timestamp()}"}


@router.get("/info")
async def get_diagnostic_info(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Return diagnostic information about the backend.

    Useful for verifying connectivity and configuration.
    """
    return {
        "status": "ok",
        "server_time": datetime.utcnow().isoformat(),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.headers.get("x-request-id"),
        "username": current_user.username,
    }
