"""User model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """User table for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_disabled = Column(Boolean, nullable=False, default=False)
    force_password_reset = Column(Boolean, nullable=False, default=False)
    is_email_verified = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    last_login_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    settings = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    tags = relationship(
        "Tag",
        back_populates="owner",
        cascade="all, delete-orphan",
        primaryjoin="User.id==Tag.owner_user_id",
    )
    jobs = relationship("Job", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
