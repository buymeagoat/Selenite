"""Schemas for feedback submissions."""

from datetime import datetime
from pydantic import BaseModel


class FeedbackAttachmentResponse(BaseModel):
    id: int
    filename: str
    content_type: str | None = None
    size_bytes: int


class FeedbackSubmissionResponse(BaseModel):
    id: int
    category: str
    subject: str | None = None
    message: str
    submitter_name: str | None = None
    submitter_email: str | None = None
    recipient_email: str | None = None
    is_anonymous: bool
    user_id: int | None = None
    sender_user_id: int | None = None
    direction: str
    folder: str
    is_read: bool
    parent_id: int | None = None
    thread_id: int | None = None
    email_status: str
    webhook_status: str
    delivery_error: str | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    attachments: list[FeedbackAttachmentResponse]


class FeedbackListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[FeedbackSubmissionResponse]


class FeedbackDetailResponse(BaseModel):
    message: FeedbackSubmissionResponse
    thread: list[FeedbackSubmissionResponse]


class FeedbackReplyRequest(BaseModel):
    message: str
    subject: str | None = None
