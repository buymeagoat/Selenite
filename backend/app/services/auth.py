"""Authentication service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from datetime import timedelta

from app.utils.security import verify_password, create_access_token


async def authenticate_user(
    db: AsyncSession,
    identifier: str,
    password: str,
    *,
    include_disabled: bool = False,
) -> Optional[User]:
    """
    Authenticate a user by email (or admin username) and password.

    Args:
        db: Database session
        identifier: Email address or admin username
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    ident = identifier.strip().lower()
    stmt = select(User)
    if ident == "admin":
        stmt = stmt.where(User.username == "admin")
    else:
        stmt = stmt.where(User.email == ident)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.is_disabled and not include_disabled:
        return None
    return user if verify_password(password, user.hashed_password) else None


def create_token_response(user: User, *, expires_minutes: int) -> TokenResponse:
    """
    Create a JWT token response for an authenticated user.

    Args:
        user: Authenticated user

    Returns:
        TokenResponse with access token
    """
    # Create token with user data
    token_data = {
        "sub": user.username,
        "user_id": user.id,
    }

    access_token = create_access_token(token_data, expires_delta=timedelta(minutes=expires_minutes))

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
        user=UserResponse.model_validate(user),
    )
