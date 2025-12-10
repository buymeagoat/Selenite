"""System-level preferences (single row)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.types import Boolean

from app.database import Base


class SystemPreferences(Base):
    """Stores server-scoped preferences such as time zone."""

    __tablename__ = "system_preferences"

    id = Column(Integer, primary_key=True)
    server_time_zone = Column(String(100), nullable=False, default="UTC")
    transcode_to_wav = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def touch(self):
        self.updated_at = datetime.utcnow()
