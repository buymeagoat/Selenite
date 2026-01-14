"""Admin user management routes."""

import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.feedback import FeedbackAttachment, FeedbackSubmission
from app.models.system_preferences import SystemPreferences
from app.models.tag import Tag
from app.models.user import User
from app.models.job import Job
from app.routes.auth import get_current_user
from app.schemas.users import (
    ActiveUserItem,
    ActiveUsersResponse,
    UserCreateRequest,
    UserListItem,
    UserListResponse,
    UserUpdateRequest,
)
from app.services.audit import log_audit_event
from app.utils.password_policy import validate_password_policy
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )


async def _get_system_preferences(db: AsyncSession) -> SystemPreferences:
    result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = SystemPreferences(id=1)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return UserListResponse(items=[UserListItem.model_validate(u) for u in users])


@router.get("/active", response_model=ActiveUsersResponse)
async def list_active_users(
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    prefs = await _get_system_preferences(db)
    window = window_minutes or prefs.session_timeout_minutes or 30
    threshold = datetime.utcnow() - timedelta(minutes=window)
    last_seen_expr = func.coalesce(User.last_seen_at, User.last_login_at)

    result = await db.execute(
        select(User)
        .where(last_seen_expr.is_not(None))
        .where(last_seen_expr >= threshold)
        .order_by(last_seen_expr.desc())
    )
    users = result.scalars().all()
    items = [
        ActiveUserItem(
            id=user.id,
            username=user.username,
            email=user.email,
            last_seen_at=user.last_seen_at or user.last_login_at,
        )
        for user in users
    ]
    return ActiveUsersResponse(total=len(items), items=items)


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    prefs = await _get_system_preferences(db)
    policy_errors = validate_password_policy(payload.password, prefs)
    if policy_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_errors[0])

    user = User(
        username=email,
        email=email,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_disabled=False,
        force_password_reset=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_audit_event(
        db,
        action="admin.user_created",
        actor=current_user,
        target_type="user",
        target_id=str(user.id),
        metadata={"email": email, "is_admin": payload.is_admin},
        request=request,
    )
    return UserListItem.model_validate(user)


@router.patch("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_root_admin = user.username == "admin"
    if is_root_admin:
        if payload.is_admin is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root admin cannot be demoted",
            )
        if payload.is_disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root admin cannot be disabled",
            )

    updates: dict[str, object] = {}
    if payload.email is not None:
        email = payload.email.strip().lower()
        if email != user.email:
            conflict = await db.execute(select(User).where(User.email == email))
            if conflict.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
                )
            user.email = email
            user.username = email
            updates["email"] = email
    if payload.password is not None:
        prefs = await _get_system_preferences(db)
        policy_errors = validate_password_policy(payload.password, prefs)
        if policy_errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_errors[0])
        user.hashed_password = hash_password(payload.password)
        updates["password_reset"] = True
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
        updates["is_admin"] = payload.is_admin
    if payload.is_disabled is not None:
        user.is_disabled = payload.is_disabled
        updates["is_disabled"] = payload.is_disabled
    if payload.force_password_reset is not None:
        user.force_password_reset = payload.force_password_reset
        updates["force_password_reset"] = payload.force_password_reset

    await db.commit()
    await db.refresh(user)
    if updates:
        await log_audit_event(
            db,
            action="admin.user_updated",
            actor=current_user,
            target_type="user",
            target_id=str(user.id),
            metadata=updates,
            request=request,
        )
    return UserListItem.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Root admin cannot be deleted",
        )

    active_result = await db.execute(
        select(Job.id).where(
            Job.user_id == user.id,
            Job.status.in_(["queued", "processing", "pausing", "cancelling"]),
        )
    )
    active_jobs = active_result.scalars().all()
    if active_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has active jobs. Cancel them before deleting the user.",
        )

    def resolve_path(path: Path) -> Path:
        return (
            path if path.is_absolute() else (Path(__file__).parent.parent.parent / path).resolve()
        )

    # Delete job files and records.
    jobs_result = await db.execute(select(Job).where(Job.user_id == user.id))
    jobs = jobs_result.scalars().all()
    for job in jobs:
        files_to_delete: set[Path] = set()
        if job.file_path:
            files_to_delete.add(resolve_path(Path(job.file_path)))
        if job.saved_filename:
            files_to_delete.add(Path(settings.media_storage_path) / job.saved_filename)
        if job.transcript_path:
            tp = resolve_path(Path(job.transcript_path))
            files_to_delete.add(tp)
            files_to_delete.add(tp.with_suffix(".json"))
        transcript_root = Path(settings.transcript_storage_path)
        files_to_delete.add(transcript_root / f"{job.id}.txt")
        files_to_delete.add((transcript_root / f"{job.id}.txt").with_suffix(".json"))
        for ext in [".md", ".srt", ".vtt", ".json", ".docx"]:
            files_to_delete.add(transcript_root / f"{job.id}{ext}")
        for file_path in files_to_delete:
            try:
                fp = resolve_path(file_path)
                if fp.exists() and fp.is_file():
                    os.remove(fp)
            except Exception:
                pass
        await db.delete(job)

    # Delete feedback attachments and submissions tied to the user.
    submission_ids = select(FeedbackSubmission.id).where(
        (FeedbackSubmission.user_id == user.id) | (FeedbackSubmission.sender_user_id == user.id)
    )
    attachments_result = await db.execute(
        select(FeedbackAttachment).where(FeedbackAttachment.submission_id.in_(submission_ids))
    )
    attachments = attachments_result.scalars().all()
    for attachment in attachments:
        try:
            path = Path(attachment.storage_path)
            if path.exists() and path.is_file():
                os.remove(path)
            parent = path.parent
            if parent.exists() and parent.is_dir():
                try:
                    parent.rmdir()
                except OSError:
                    pass
        except Exception:
            pass

    await db.execute(
        delete(FeedbackSubmission).where(
            (FeedbackSubmission.user_id == user.id) | (FeedbackSubmission.sender_user_id == user.id)
        )
    )

    # Delete personal tags and audit logs.
    await db.execute(delete(Tag).where(Tag.owner_user_id == user.id))
    await db.execute(delete(AuditLog).where(AuditLog.actor_user_id == user.id))
    await db.execute(
        delete(AuditLog).where(
            (AuditLog.target_type == "user") & (AuditLog.target_id == str(user.id))
        )
    )

    await log_audit_event(
        db,
        action="admin.user_deleted",
        actor=current_user,
        target_type="user",
        target_id=str(user.id),
        metadata={"email": user.email, "username": user.username},
        request=request,
    )

    await db.delete(user)
    await db.commit()
    return None
