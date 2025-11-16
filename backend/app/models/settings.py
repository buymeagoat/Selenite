"""Settings model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey
from app.database import Base


class Settings(Base):
    """User settings table."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Transcription defaults
    default_model = Column(String(20), nullable=False, default="medium")
    default_language = Column(String(10), nullable=False, default="auto")
    default_timestamps = Column(Boolean, nullable=False, default=True)
    default_speaker_detection = Column(Boolean, nullable=False, default=True)

    # System settings
    max_concurrent_jobs = Column(Integer, nullable=False, default=3)
    storage_location = Column(String(512), nullable=False, default="/storage")
    storage_limit_bytes = Column(BigInteger, nullable=False, default=107374182400)  # 100GB

    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Settings(id={self.id}, user_id={self.user_id}, default_model='{self.default_model}')>"
