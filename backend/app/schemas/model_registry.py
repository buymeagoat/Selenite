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


class ModelWeightCreate(BaseModel):
    """Payload for registering a model weight under a set."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: str = Field(..., min_length=1, max_length=1024)
    checksum: Optional[str] = Field(default=None, max_length=128)


class ModelWeightUpdate(BaseModel):
    """Payload for updating a model weight."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    abs_path: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    checksum: Optional[str] = Field(default=None, max_length=128)
    enabled: Optional[bool] = None
    disable_reason: Optional[str] = None


class ModelWeightResponse(BaseModel):
    """Response model for weights."""

    id: int
    set_id: int
    type: ProviderType
    name: str
    description: Optional[str]
    checksum: Optional[str]
    abs_path: str
    enabled: bool
    disable_reason: Optional[str]
    has_weights: bool = False
    force_enabled: bool = False
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


class ModelSetWithWeights(ModelSetResponse):
    weights: list[ModelWeightResponse]
