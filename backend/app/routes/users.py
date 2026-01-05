"""Admin user management routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.users import UserCreateRequest, UserListResponse, UserListItem, UserUpdateRequest
from app.services.audit import log_audit_event
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return UserListResponse(items=[UserListItem.model_validate(u) for u in users])


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
