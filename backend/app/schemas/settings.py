"""Schemas for user settings persistence."""

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    default_model: str
    default_language: str
    max_concurrent_jobs: int


class SettingsUpdateRequest(BaseModel):
    default_model: str = Field(
        default="medium", pattern="^(tiny|base|small|medium|large|large-v3)$"
    )
    default_language: str = Field(default="auto", max_length=10)
    max_concurrent_jobs: int = Field(default=3, ge=1, le=10)
