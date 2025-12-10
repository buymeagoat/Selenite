"""Pydantic schemas for the model registry."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ProviderType = Literal["asr", "diarizer"]


class ModelSetCreate(BaseModel):
    """Payload for registering a new model set."""

    type: ProviderType
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: str = Field(..., min_length=1, max_length=1024)


class ModelSetUpdate(BaseModel):
    """Payload for updating a model set."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    enabled: Optional[bool] = None
    disable_reason: Optional[str] = None


class ModelEntryCreate(BaseModel):
    """Payload for registering a model entry under a set."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: str = Field(..., min_length=1, max_length=1024)
    checksum: Optional[str] = Field(default=None, max_length=128)


class ModelEntryUpdate(BaseModel):
    """Payload for updating a model entry."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    checksum: Optional[str] = Field(default=None, max_length=128)
    enabled: Optional[bool] = None
    disable_reason: Optional[str] = None


class ModelEntryResponse(BaseModel):
    """Response model for entries."""

    id: int
    set_id: int
    type: ProviderType
    name: str
    description: Optional[str]
    checksum: Optional[str]
    abs_path: str
    enabled: bool
    disable_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelSetResponse(BaseModel):
    """Response model for model sets without entries attached."""

    id: int
    type: ProviderType
    name: str
    description: Optional[str]
    abs_path: str
    enabled: bool
    disable_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelSetWithEntries(ModelSetResponse):
    entries: list[ModelEntryResponse]
