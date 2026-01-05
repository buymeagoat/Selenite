"""Authentication routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
)
from app.services.auth import authenticate_user, create_token_response
from app.services.audit import log_audit_event
from app.utils.security import decode_access_token
from app.models.user import User
from sqlalchemy import select
from app.utils.security import verify_password, hash_password

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT token.

    Args:
        credentials: Login credentials (email or admin username and password)
        db: Database session

    Returns:
        TokenResponse with access token

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(
        db,
        credentials.email,
        credentials.password,
        include_disabled=True,
    )

    if not user:
        await log_audit_event(
            db,
            action="auth.login_failed",
            actor=None,
            target_type="user",
            target_id=credentials.email,
            metadata={"identifier": credentials.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.is_disabled:
        await log_audit_event(
            db,
            action="auth.login_disabled",
            actor=None,
            target_type="user",
            target_id=str(user.id),
            metadata={"identifier": credentials.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    user.last_login_at = datetime.utcnow()
    await db.commit()
    await log_audit_event(
        db,
        action="auth.login_success",
        actor=user,
        target_type="user",
        target_id=str(user.id),
        metadata={"identifier": credentials.email},
        request=request,
    )

    return create_token_response(user)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token: str | None = Query(None, description="JWT bearer token (optional)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    bearer = credentials.credentials if credentials else token
    if not bearer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization header missing",
        )

    # Decode token
    payload = decode_access_token(bearer)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Get user from database
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        UserResponse with user information
    """
    return UserResponse.model_validate(current_user)


@router.put("/password", response_model=PasswordChangeResponse)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password after verifying current password and confirmation.

    Raises:
        HTTPException: 400 if confirmation mismatch
        HTTPException: 401 if current password invalid
    """
    # Confirm match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Verify current password
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Reject reuse
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400, detail="New password must differ from current password"
        )

    # Update hash
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.force_password_reset = False
    await db.commit()
    await db.refresh(current_user)

    return PasswordChangeResponse(detail="Password changed successfully")
