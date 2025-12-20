"""Job model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Job(Base):
    """Job table for transcription jobs.

    Status values:
    queued      - Waiting to be picked up by a worker
    processing  - Actively being transcribed
    cancelling  - Cancellation requested; worker is draining work in progress
    completed   - Finished successfully
    failed      - Processing ended with an error
    cancelled   - Cancellation confirmed (queued job or worker acknowledged)
    """

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    saved_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String(100), nullable=True)
    duration = Column(Float, nullable=True)  # seconds
    status = Column(
        String(20), nullable=False, index=True
    )  # queued, processing, cancelling, completed, failed, cancelled
    progress_percent = Column(Integer, default=0, nullable=False)
    progress_stage = Column(String(50), nullable=True)
    estimated_time_left = Column(Integer, nullable=True)  # seconds
    model_used = Column(String(20), nullable=True)
    asr_provider_used = Column(String(50), nullable=True)
    language_detected = Column(String(10), nullable=True)
    speaker_count = Column(Integer, nullable=True)
    has_timestamps = Column(Boolean, default=True, nullable=False)
    has_speaker_labels = Column(Boolean, default=True, nullable=False)
    diarizer_used = Column(String(20), nullable=True)
    diarizer_provider_used = Column(String(50), nullable=True)
    transcript_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_total_seconds = Column(Integer, nullable=True)
    stalled_at = Column(DateTime, nullable=True)

    # Relationships
    tags = relationship("Tag", secondary="job_tags", back_populates="jobs")
    transcripts = relationship("Transcript", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Job(id='{self.id}', filename='{self.original_filename}', status='{self.status}')>"
