"""Pydantic schemas for transcript retrieval."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A single transcript segment."""

    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Response schema for GET /transcripts/{job_id}."""

    job_id: str
    text: str
    segments: List[TranscriptSegment]
    language: str
    duration: float
    has_timestamps: bool
    has_speaker_labels: bool


class SpeakerLabelUpdate(BaseModel):
    """Rename a speaker label in a transcript."""

    label: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=80)


class SpeakerLabelUpdateRequest(BaseModel):
    """Request payload for updating speaker labels."""

    updates: List[SpeakerLabelUpdate]


class SpeakerLabelsResponse(BaseModel):
    """Response payload for available speaker labels."""

    speakers: List[str]
