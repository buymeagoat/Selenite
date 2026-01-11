"""System-level preferences (single row)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.types import Boolean

from app.database import Base


class SystemPreferences(Base):
    """Stores server-scoped preferences such as time zone."""

    __tablename__ = "system_preferences"

    id = Column(Integer, primary_key=True)
    server_time_zone = Column(String(100), nullable=False, default="UTC")
    transcode_to_wav = Column(Boolean, nullable=False, default=True)
    enable_empty_weights = Column(Boolean, nullable=False, default=False)
    default_tags_seeded = Column(Boolean, nullable=False, default=False)
    feedback_store_enabled = Column(Boolean, nullable=False, default=True)
    feedback_email_enabled = Column(Boolean, nullable=False, default=False)
    feedback_webhook_enabled = Column(Boolean, nullable=False, default=False)
    feedback_destination_email = Column(String(255), nullable=True)
    feedback_webhook_url = Column(String(512), nullable=True)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_use_tls = Column(Boolean, nullable=False, default=True)
    session_timeout_minutes = Column(Integer, nullable=False, default=30)
    auth_token_not_before = Column(DateTime, nullable=True)
    allow_self_signup = Column(Boolean, nullable=False, server_default=text("0"), default=False)
    require_signup_verification = Column(
        Boolean, nullable=False, server_default=text("0"), default=False
    )
    require_signup_captcha = Column(Boolean, nullable=False, server_default=text("1"), default=True)
    signup_captcha_provider = Column(String(50), nullable=True, default="turnstile")
    signup_captcha_site_key = Column(String(255), nullable=True)
    password_min_length = Column(Integer, nullable=False, server_default=text("12"), default=12)
    password_require_uppercase = Column(
        Boolean, nullable=False, server_default=text("1"), default=True
    )
    password_require_lowercase = Column(
        Boolean, nullable=False, server_default=text("1"), default=True
    )
    password_require_number = Column(
        Boolean, nullable=False, server_default=text("1"), default=True
    )
    password_require_special = Column(
        Boolean, nullable=False, server_default=text("0"), default=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def touch(self):
        self.updated_at = datetime.utcnow()
