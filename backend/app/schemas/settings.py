"""Schemas for user settings persistence."""

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    default_asr_provider: str | None = None
    default_model: str
    default_language: str
    default_diarizer_provider: str | None = None
    default_diarizer: str
    diarization_enabled: bool
    allow_job_overrides: bool
    enable_timestamps: bool
    max_concurrent_jobs: int
    time_zone: str | None = None
    server_time_zone: str
    transcode_to_wav: bool
    enable_empty_weights: bool
    last_selected_asr_set: str | None = None
    last_selected_diarizer_set: str | None = None


class SettingsUpdateRequest(BaseModel):
    default_asr_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, max_length=10)
    default_diarizer_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_diarizer: str | None = Field(default=None, min_length=1, max_length=200)
    diarization_enabled: bool | None = Field(default=None)
    allow_job_overrides: bool | None = Field(default=None)
    enable_timestamps: bool | None = Field(default=None)
    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    time_zone: str | None = Field(default=None, max_length=100)
    server_time_zone: str | None = Field(default=None, max_length=100)
    transcode_to_wav: bool | None = Field(default=None)
    enable_empty_weights: bool | None = Field(default=None)
    last_selected_asr_set: str | None = Field(default=None, min_length=1, max_length=255)
    last_selected_diarizer_set: str | None = Field(default=None, min_length=1, max_length=255)


class SettingsUpdateAsr(BaseModel):
    default_asr_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, max_length=10)
    allow_job_overrides: bool | None = Field(default=None)
    enable_timestamps: bool | None = Field(default=None)
    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    time_zone: str | None = Field(default=None, max_length=100)
    last_selected_asr_set: str | None = Field(default=None, min_length=1, max_length=255)


class SettingsUpdateDiarization(BaseModel):
    default_diarizer_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_diarizer: str | None = Field(default=None, min_length=1, max_length=200)
    diarization_enabled: bool | None = Field(default=None)
    allow_job_overrides: bool | None = Field(default=None)
    time_zone: str | None = Field(default=None, max_length=100)
    last_selected_diarizer_set: str | None = Field(default=None, min_length=1, max_length=255)
