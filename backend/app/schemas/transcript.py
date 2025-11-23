"""Pydantic schemas for transcript retrieval."""

from typing import List, Optional
from pydantic import BaseModel


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
