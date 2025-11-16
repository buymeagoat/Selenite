"""Transcript model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Transcript(Base):
    """Transcript table for storing generated transcripts in various formats."""

    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format = Column(String(10), nullable=False)  # txt, md, srt, vtt, json, docx
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="transcripts")

    def __repr__(self) -> str:
        return f"<Transcript(id={self.id}, job_id='{self.job_id}', format='{self.format}')>"
