"""Schemas for user settings persistence."""

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    default_asr_provider: str | None = None
    default_model: str
    default_language: str
    default_diarizer_provider: str | None = None
    default_diarizer: str
    diarization_enabled: bool
    allow_asr_overrides: bool
    allow_diarizer_overrides: bool
    enable_timestamps: bool
    max_concurrent_jobs: int
    show_all_jobs: bool
    time_zone: str | None = None
    date_format: str | None = None
    time_format: str | None = None
    locale: str | None = None
    server_time_zone: str
    transcode_to_wav: bool
    enable_empty_weights: bool
    last_selected_asr_set: str | None = None
    last_selected_diarizer_set: str | None = None
    feedback_store_enabled: bool
    feedback_email_enabled: bool
    feedback_webhook_enabled: bool
    feedback_destination_email: str | None = None
    feedback_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool
    smtp_password_set: bool = False
    session_timeout_minutes: int
    allow_self_signup: bool
    require_signup_verification: bool
    require_signup_captcha: bool
    signup_captcha_provider: str | None = None
    signup_captcha_site_key: str | None = None
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_number: bool
    password_require_special: bool


class SettingsUpdateRequest(BaseModel):
    default_asr_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, max_length=10)
    default_diarizer_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_diarizer: str | None = Field(default=None, min_length=1, max_length=200)
    diarization_enabled: bool | None = Field(default=None)
    allow_asr_overrides: bool | None = Field(default=None)
    allow_diarizer_overrides: bool | None = Field(default=None)
    enable_timestamps: bool | None = Field(default=None)
    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    show_all_jobs: bool | None = Field(default=None)
    time_zone: str | None = Field(default=None, max_length=100)
    date_format: str | None = Field(default=None, max_length=20)
    time_format: str | None = Field(default=None, max_length=20)
    locale: str | None = Field(default=None, max_length=64)
    server_time_zone: str | None = Field(default=None, max_length=100)
    transcode_to_wav: bool | None = Field(default=None)
    enable_empty_weights: bool | None = Field(default=None)
    last_selected_asr_set: str | None = Field(default=None, min_length=1, max_length=255)
    last_selected_diarizer_set: str | None = Field(default=None, min_length=1, max_length=255)
    feedback_store_enabled: bool | None = Field(default=None)
    feedback_email_enabled: bool | None = Field(default=None)
    feedback_webhook_enabled: bool | None = Field(default=None)
    feedback_destination_email: str | None = Field(default=None, max_length=255)
    feedback_webhook_url: str | None = Field(default=None, max_length=512)
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, max_length=255)
    smtp_password: str | None = Field(default=None, max_length=255)
    smtp_from_email: str | None = Field(default=None, max_length=255)
    smtp_use_tls: bool | None = Field(default=None)
    session_timeout_minutes: int | None = Field(default=None, ge=5, le=1440)
    allow_self_signup: bool | None = Field(default=None)
    require_signup_verification: bool | None = Field(default=None)
    require_signup_captcha: bool | None = Field(default=None)
    signup_captcha_provider: str | None = Field(default=None, min_length=2, max_length=50)
    signup_captcha_site_key: str | None = Field(default=None, min_length=1, max_length=255)
    password_min_length: int | None = Field(default=None, ge=8, le=256)
    password_require_uppercase: bool | None = Field(default=None)
    password_require_lowercase: bool | None = Field(default=None)
    password_require_number: bool | None = Field(default=None)
    password_require_special: bool | None = Field(default=None)


class SettingsUpdateAsr(BaseModel):
    default_asr_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    default_language: str | None = Field(default=None, max_length=10)
    allow_asr_overrides: bool | None = Field(default=None)
    enable_timestamps: bool | None = Field(default=None)
    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=10)
    show_all_jobs: bool | None = Field(default=None)
    time_zone: str | None = Field(default=None, max_length=100)
    last_selected_asr_set: str | None = Field(default=None, min_length=1, max_length=255)


class SettingsUpdateDiarization(BaseModel):
    default_diarizer_provider: str | None = Field(default=None, min_length=1, max_length=255)
    default_diarizer: str | None = Field(default=None, min_length=1, max_length=200)
    diarization_enabled: bool | None = Field(default=None)
    allow_diarizer_overrides: bool | None = Field(default=None)
    show_all_jobs: bool | None = Field(default=None)
    time_zone: str | None = Field(default=None, max_length=100)
    last_selected_diarizer_set: str | None = Field(default=None, min_length=1, max_length=255)
