"""Feedback submission models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class FeedbackSubmission(Base):
    """Stores feedback submitted by users or anonymous visitors."""

    __tablename__ = "feedback_submissions"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False, default="comment")
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    submitter_name = Column(String(200), nullable=True)
    submitter_email = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    is_anonymous = Column(Boolean, nullable=False, default=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    direction = Column(String(20), nullable=False, default="incoming")
    folder = Column(String(20), nullable=False, default="inbox")
    is_read = Column(Boolean, nullable=False, default=False)
    parent_id = Column(
        Integer, ForeignKey("feedback_submissions.id", ondelete="SET NULL"), nullable=True
    )
    thread_id = Column(
        Integer, ForeignKey("feedback_submissions.id", ondelete="SET NULL"), nullable=True
    )
    email_status = Column(String(50), nullable=False, default="pending")
    webhook_status = Column(String(50), nullable=False, default="pending")
    delivery_error = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    attachments = relationship(
        "FeedbackAttachment",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    parent = relationship("FeedbackSubmission", remote_side=[id], foreign_keys=[parent_id])

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class FeedbackAttachment(Base):
    """Attachment metadata for a feedback submission."""

    __tablename__ = "feedback_attachments"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("feedback_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    storage_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submission = relationship("FeedbackSubmission", back_populates="attachments")
