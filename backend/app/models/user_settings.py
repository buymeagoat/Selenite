"""User settings model for default transcription preferences and concurrency."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class UserSettings(Base):
    """Per-user settings.

    Fields:
    - default_model: Whisper model key (tiny/base/small/medium/large)
    - default_language: Language code or 'auto'
    - max_concurrent_jobs: Job queue worker concurrency (1..10)
    """

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    default_asr_provider = Column(String(255), nullable=True)
    default_model = Column(String(20), nullable=False, default="medium")
    default_language = Column(String(10), nullable=False, default="auto")
    default_diarizer = Column(String(20), nullable=False, default="vad")
    default_diarizer_provider = Column(String(255), nullable=True)
    diarization_enabled = Column(Boolean, nullable=False, default=False)
    allow_asr_overrides = Column(Boolean, nullable=False, default=False)
    allow_diarizer_overrides = Column(Boolean, nullable=False, default=False)
    enable_timestamps = Column(Boolean, nullable=False, default=True)
    max_concurrent_jobs = Column(Integer, nullable=False, default=3)
    time_zone = Column(String(100), nullable=True)
    last_selected_asr_set = Column(String(255), nullable=True)
    last_selected_diarizer_set = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="settings", uselist=False)

    def touch(self):  # update timestamp helper
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:  # pragma: no cover simple repr
        return f"<UserSettings(user_id={self.user_id}, model={self.default_model}, lang={self.default_language}, conc={self.max_concurrent_jobs})>"
