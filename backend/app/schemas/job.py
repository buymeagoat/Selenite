"""Pydantic schemas for job management."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    """Response schema for tag information."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    color: Optional[str] = None


class TagAssignRequest(BaseModel):
    """Request schema for assigning/creating a tag on a job.

    Either provide an existing tag id or a name (with optional color) to create/reuse.
    """

    tag_ids: Optional[List[int]] = None


class JobCreate(BaseModel):
    """Request schema for creating a new transcription job."""

    model: str = Field(default="medium", pattern="^(tiny|base|small|medium|large|large-v3)$")
    language: str = Field(default="auto", max_length=10)
    enable_timestamps: bool = Field(default=True)
    enable_speaker_detection: bool = Field(default=False)
    speaker_count: Optional[int] = None


class JobResponse(BaseModel):
    """Response schema for job information."""

    model_config = {"from_attributes": True}

    id: UUID
    original_filename: str
    saved_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: int
    mime_type: str
    duration: Optional[float] = None
    status: str
    progress_percent: int = 0
    progress_stage: Optional[str] = None
    estimated_time_left: Optional[int] = None
    estimated_total_seconds: Optional[int] = None
    processing_seconds: Optional[int] = 0
    model_used: str
    asr_provider_used: Optional[str] = None
    diarizer_used: Optional[str] = None
    diarizer_provider_used: Optional[str] = None
    language_detected: Optional[str] = None
    speaker_count: Optional[int] = None
    has_timestamps: bool
    has_speaker_labels: bool
    transcript_path: Optional[str] = None
    error_message: Optional[str] = None
    tags: List[TagResponse] = []
    owner_user_id: Optional[int] = None
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    available_exports: List[str] = ["txt", "md", "srt", "vtt", "json", "docx"]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stalled_at: Optional[datetime] = None
    pause_requested_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resume_count: Optional[int] = None


class JobRenameRequest(BaseModel):
    """Request schema for renaming a job."""

    name: str = Field(..., min_length=1, max_length=255)


class JobListItem(BaseModel):
    """Simplified job schema for list view."""

    model_config = {"from_attributes": True}

    id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    duration: Optional[float] = None
    status: str
    progress_percent: int = 0
    progress_stage: Optional[str] = None
    estimated_time_left: Optional[int] = None
    estimated_total_seconds: Optional[int] = None
    processing_seconds: Optional[int] = 0
    model_used: str
    asr_provider_used: Optional[str] = None
    diarizer_used: Optional[str] = None
    diarizer_provider_used: Optional[str] = None
    language_detected: Optional[str] = None
    speaker_count: Optional[int] = None
    has_timestamps: bool
    has_speaker_labels: bool
    tags: List[TagResponse] = []
    owner_user_id: Optional[int] = None
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stalled_at: Optional[datetime] = None
    pause_requested_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resume_count: Optional[int] = None


class JobListResponse(BaseModel):
    """Response schema for paginated job list."""

    total: int
    limit: int
    offset: int
    items: List[JobListItem]


class JobStatusResponse(BaseModel):
    """Response schema for job status polling (optimized)."""

    model_config = {"from_attributes": True}

    id: UUID
    status: str
    progress_percent: int
    progress_stage: Optional[str] = None
    estimated_time_left: Optional[int] = None
    estimated_total_seconds: Optional[int] = None
    processing_seconds: Optional[int] = 0
    updated_at: Optional[datetime] = None
    stalled_at: Optional[datetime] = None
    pause_requested_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resume_count: Optional[int] = None


class JobCreatedResponse(BaseModel):
    """Response schema for newly created job."""

    model_config = {"from_attributes": True}

    id: UUID
    original_filename: str
    status: str
    created_at: datetime
