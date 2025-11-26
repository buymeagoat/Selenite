"""Schemas for user settings persistence."""

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    default_model: str
    default_language: str
    default_diarizer: str
    diarization_enabled: bool
    allow_job_overrides: bool
    max_concurrent_jobs: int


class SettingsUpdateRequest(BaseModel):
    default_model: str = Field(
        default="medium", pattern="^(tiny|base|small|medium|large|large-v3)$"
    )
    default_language: str = Field(default="auto", max_length=10)
    default_diarizer: str = Field(default="vad", pattern="^(whisperx|pyannote|vad)$")
    diarization_enabled: bool = Field(default=False)
    allow_job_overrides: bool = Field(default=False)
    max_concurrent_jobs: int = Field(default=3, ge=1, le=10)
