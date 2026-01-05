"""Schemas for admin user management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class UserListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool
    is_disabled: bool
    force_password_reset: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_admin: bool = False


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_admin: Optional[bool] = None
    is_disabled: Optional[bool] = None
    force_password_reset: Optional[bool] = None


class UserListResponse(BaseModel):
    items: list[UserListItem]
