"""Authentication service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.utils.security import verify_password, create_access_token
from app.config import settings


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    return user if user and verify_password(password, user.hashed_password) else None


def create_token_response(user: User) -> TokenResponse:
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

    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
        user=UserResponse.model_validate(user),
    )
