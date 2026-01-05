"""Audit logging helpers."""

from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_audit_event(
    db: AsyncSession,
    *,
    action: str,
    actor: Optional[User],
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """Persist an audit event without raising on failure."""
    try:
        ip_address = None
        user_agent = None
        if request is not None:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        entry = AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata or None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        await db.commit()
    except Exception:
        await db.rollback()
