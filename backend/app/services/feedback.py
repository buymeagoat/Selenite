"""Feedback submission helpers."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

import aiofiles
import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.feedback import FeedbackAttachment, FeedbackSubmission
from app.models.system_preferences import SystemPreferences
from app.utils.file_handling import sanitize_user_filename, resolve_unique_media_path

logger = logging.getLogger(__name__)

MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
    "application/pdf",
}


def normalize_category(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"bug", "suggestion", "comment"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback category must be bug, suggestion, or comment.",
        )
    return normalized


async def _write_upload(
    upload: UploadFile,
    destination: Path,
    *,
    max_bytes: int,
) -> int:
    size_bytes = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(destination, "wb") as buffer:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Attachment '{upload.filename}' exceeds size limit.",
                )
            await buffer.write(chunk)
    await upload.close()
    return size_bytes


async def save_attachments(
    db: AsyncSession,
    submission: FeedbackSubmission,
    uploads: Iterable[UploadFile],
) -> list[FeedbackAttachment]:
    uploads_list = [upload for upload in uploads if upload is not None]
    if not uploads_list:
        return []
    if len(uploads_list) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {MAX_ATTACHMENTS} attachments are allowed.",
        )
    total_bytes = 0
    stored: list[FeedbackAttachment] = []
    base_dir = Path(settings.feedback_storage_path) / str(submission.id)

    for idx, upload in enumerate(uploads_list, start=1):
        content_type = upload.content_type or "application/octet-stream"
        if content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attachment '{upload.filename}' has unsupported type.",
            )
        raw_name = upload.filename or f"attachment-{idx}"
        try:
            filename = sanitize_user_filename(raw_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attachment '{raw_name}' has an invalid filename.",
            ) from exc
        destination = resolve_unique_media_path(filename, str(base_dir))
        size_bytes = await _write_upload(upload, destination, max_bytes=MAX_ATTACHMENT_BYTES)
        total_bytes += size_bytes
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total attachment size exceeds limit.",
            )
        attachment = FeedbackAttachment(
            submission_id=submission.id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=str(destination),
        )
        db.add(attachment)
        stored.append(attachment)

    await db.commit()
    for attachment in stored:
        await db.refresh(attachment)
    return stored


def _attach_files(msg: EmailMessage, attachments: list[FeedbackAttachment]) -> None:
    for attachment in attachments:
        try:
            data = Path(attachment.storage_path).read_bytes()
        except Exception as exc:
            logger.warning("Failed to read attachment %s: %s", attachment.storage_path, exc)
            continue
        guessed_type = attachment.content_type or mimetypes.guess_type(attachment.filename)[0]
        content_type = guessed_type or "application/octet-stream"
        maintype, subtype = content_type.split("/", 1)
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )


def _build_email_message(
    prefs: SystemPreferences,
    submission: FeedbackSubmission,
    attachments: list[FeedbackAttachment],
) -> EmailMessage:
    msg = EmailMessage()
    sender = prefs.smtp_from_email or prefs.feedback_destination_email or "noreply@localhost"
    msg["From"] = sender
    msg["To"] = prefs.feedback_destination_email
    msg["Subject"] = (
        f"[Selenite Feedback] {submission.category}: {submission.subject or 'No subject'}"
    )
    lines = [
        f"Category: {submission.category}",
        f"Subject: {submission.subject or 'None'}",
        f"Submitted by: {submission.submitter_name or 'Anonymous'}",
        f"Email: {submission.submitter_email or 'Not provided'}",
        f"User ID: {submission.user_id or 'Anonymous'}",
        "",
        submission.message,
    ]
    msg.set_content("\n".join(lines))
    _attach_files(msg, attachments)
    return msg


async def send_feedback_email(
    prefs: SystemPreferences,
    submission: FeedbackSubmission,
    attachments: list[FeedbackAttachment],
) -> tuple[str, str | None]:
    if not prefs.feedback_email_enabled:
        return "skipped", None
    if not prefs.feedback_destination_email:
        return "failed", "Missing destination email."
    if not (prefs.smtp_host and prefs.smtp_port and prefs.smtp_from_email):
        return "failed", "SMTP host, port, and from address are required."

    message = _build_email_message(prefs, submission, attachments)

    def _send() -> None:
        if prefs.smtp_use_tls:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
        try:
            if prefs.smtp_username and prefs.smtp_password:
                server.login(prefs.smtp_username, prefs.smtp_password)
            server.send_message(message)
        finally:
            server.quit()

    try:
        await asyncio.to_thread(_send)
        return "sent", None
    except Exception as exc:
        logger.warning("Feedback email failed: %s", exc)
        return "failed", str(exc)


async def send_feedback_webhook(
    prefs: SystemPreferences,
    submission: FeedbackSubmission,
    attachments: list[FeedbackAttachment],
) -> tuple[str, str | None]:
    if not prefs.feedback_webhook_enabled:
        return "skipped", None
    if not prefs.feedback_webhook_url:
        return "failed", "Missing webhook URL."

    payload = {
        "id": submission.id,
        "category": submission.category,
        "subject": submission.subject,
        "message": submission.message,
        "submitter_name": submission.submitter_name,
        "submitter_email": submission.submitter_email,
        "is_anonymous": submission.is_anonymous,
        "user_id": submission.user_id,
        "created_at": submission.created_at.isoformat(),
        "attachments": [
            {
                "id": att.id,
                "filename": att.filename,
                "content_type": att.content_type,
                "size_bytes": att.size_bytes,
            }
            for att in attachments
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(prefs.feedback_webhook_url, json=payload)
            response.raise_for_status()
        return "sent", None
    except Exception as exc:
        logger.warning("Feedback webhook failed: %s", exc)
        return "failed", str(exc)


async def send_feedback_reply(
    prefs: SystemPreferences,
    submission: FeedbackSubmission,
    reply_message: str,
    *,
    reply_subject: str | None = None,
    attachments: list[FeedbackAttachment] | None = None,
) -> tuple[str, str | None]:
    if not submission.submitter_email:
        return "failed", "No submitter email on this feedback."
    if not (prefs.smtp_host and prefs.smtp_port and prefs.smtp_from_email):
        return "failed", "SMTP host, port, and from address are required."

    msg = EmailMessage()
    msg["From"] = prefs.smtp_from_email
    msg["To"] = submission.submitter_email
    msg["Subject"] = reply_subject or f"Re: {submission.subject or 'Your feedback'}"
    msg.set_content(reply_message)
    if attachments:
        _attach_files(msg, attachments)

    def _send() -> None:
        if prefs.smtp_use_tls:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
        try:
            if prefs.smtp_username and prefs.smtp_password:
                server.login(prefs.smtp_username, prefs.smtp_password)
            server.send_message(msg)
        finally:
            server.quit()

    try:
        await asyncio.to_thread(_send)
        return "sent", None
    except Exception as exc:
        logger.warning("Feedback reply failed: %s", exc)
        return "failed", str(exc)


async def send_outbound_message(
    prefs: SystemPreferences,
    recipient_email: str,
    subject: str | None,
    body: str,
    attachments: list[FeedbackAttachment],
) -> tuple[str, str | None]:
    if not (prefs.smtp_host and prefs.smtp_port and prefs.smtp_from_email):
        return "failed", "SMTP host, port, and from address are required."

    msg = EmailMessage()
    msg["From"] = prefs.smtp_from_email
    msg["To"] = recipient_email
    msg["Subject"] = subject or "Selenite message"
    msg.set_content(body)
    if attachments:
        _attach_files(msg, attachments)

    def _send() -> None:
        if prefs.smtp_use_tls:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(prefs.smtp_host, prefs.smtp_port, timeout=10)
        try:
            if prefs.smtp_username and prefs.smtp_password:
                server.login(prefs.smtp_username, prefs.smtp_password)
            server.send_message(msg)
        finally:
            server.quit()

    try:
        await asyncio.to_thread(_send)
        return "sent", None
    except Exception as exc:
        logger.warning("Outbound message failed: %s", exc)
        return "failed", str(exc)
