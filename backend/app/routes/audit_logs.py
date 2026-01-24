"""Audit log routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.audit_logs import AuditLogItem, AuditLogListResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )


def _apply_filters(
    query,
    *,
    action: Optional[str],
    actor_id: Optional[int],
    target_type: Optional[str],
    target_id: Optional[str],
    q: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
):
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if actor_id:
        query = query.where(AuditLog.actor_user_id == actor_id)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
    if target_id:
        query = query.where(AuditLog.target_id == target_id)
    if since:
        query = query.where(AuditLog.created_at >= since)
    if until:
        query = query.where(AuditLog.created_at <= until)
    if q:
        like = f"%{q}%"
        query = query.where(
            (AuditLog.action.ilike(like))
            | (AuditLog.target_type.ilike(like))
            | (AuditLog.target_id.ilike(like))
        )
    return query


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(default=None),
    actor_id: Optional[int] = Query(default=None),
    target_type: Optional[str] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    base_query = select(AuditLog).order_by(AuditLog.created_at.desc())
    filtered = _apply_filters(
        base_query,
        action=action,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        q=q,
        since=since,
        until=until,
    )

    total_query = _apply_filters(
        select(func.count(AuditLog.id)),
        action=action,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        q=q,
        since=since,
        until=until,
    )
    total = (await db.execute(total_query)).scalar() or 0

    result = await db.execute(filtered.limit(limit).offset(offset))
    logs = result.scalars().all()

    actor_ids = {log.actor_user_id for log in logs if log.actor_user_id}
    actors = {}
    if actor_ids:
        actor_result = await db.execute(select(User).where(User.id.in_(actor_ids)))
        actors = {user.id: user for user in actor_result.scalars().all()}

    items = [
        AuditLogItem(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_email=(
                actors.get(log.actor_user_id).email if log.actor_user_id in actors else None
            ),
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            metadata=log.metadata_json,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log in logs
    ]
    return AuditLogListResponse(total=total, items=items)


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = Query(default=None),
    actor_id: Optional[int] = Query(default=None),
    target_type: Optional[str] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    query = _apply_filters(
        select(AuditLog).order_by(AuditLog.created_at.desc()),
        action=action,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        q=q,
        since=since,
        until=until,
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    lines = [
        "id,created_at,action,actor_user_id,actor_email,target_type,target_id,ip_address,user_agent"
    ]
    actor_ids = {log.actor_user_id for log in logs if log.actor_user_id}
    actors = {}
    if actor_ids:
        actor_result = await db.execute(select(User).where(User.id.in_(actor_ids)))
        actors = {user.id: user for user in actor_result.scalars().all()}

    for log in logs:
        actor_email = actors.get(log.actor_user_id).email if log.actor_user_id in actors else ""
        fields = [
            str(log.id),
            log.created_at.isoformat(),
            log.action,
            str(log.actor_user_id) if log.actor_user_id else "",
            actor_email,
            log.target_type or "",
            log.target_id or "",
            log.ip_address or "",
            (log.user_agent or "").replace('"', '""'),
        ]
        line = ",".join(f'"{value}"' for value in fields)
        lines.append(line)

    csv_data = "\n".join(lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
