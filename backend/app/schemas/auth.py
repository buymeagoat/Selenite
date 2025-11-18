"""Pydantic schemas for authentication."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Response schema for successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """Response schema for user information."""

    model_config = {"from_attributes": True}

    id: int
    username: str
    email: Optional[str] = None
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    """Request schema for password change."""

    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    def validate_match(self) -> None:
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")


class PasswordChangeResponse(BaseModel):
    """Response for successful password change."""

    detail: str = Field(..., example="Password changed successfully")
