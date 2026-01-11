"""Feedback submission routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
    Query,
    Request,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.feedback import FeedbackSubmission, FeedbackAttachment
from app.models.system_preferences import SystemPreferences
from app.models.user import User
from app.schemas.feedback import (
    FeedbackSubmissionResponse,
    FeedbackListResponse,
    FeedbackReplyRequest,
)
from app.services.feedback import (
    normalize_category,
    save_attachments,
    send_feedback_email,
    send_feedback_webhook,
    send_feedback_reply,
)
from app.routes.auth import get_current_user
from app.services.audit import log_audit_event


router = APIRouter(prefix="/feedback", tags=["feedback"])


async def _get_system_preferences(db: AsyncSession) -> SystemPreferences:
    result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = SystemPreferences(id=1)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


def _serialize_submission(
    submission: FeedbackSubmission,
    attachments: list[FeedbackAttachment] | None = None,
) -> FeedbackSubmissionResponse:
    resolved_attachments = attachments if attachments is not None else submission.attachments
    return FeedbackSubmissionResponse(
        id=submission.id,
        category=submission.category,
        subject=submission.subject,
        message=submission.message,
        submitter_name=submission.submitter_name,
        submitter_email=submission.submitter_email,
        recipient_email=submission.recipient_email,
        is_anonymous=submission.is_anonymous,
        user_id=submission.user_id,
        sender_user_id=submission.sender_user_id,
        direction=submission.direction,
        folder=submission.folder,
        is_read=submission.is_read,
        parent_id=submission.parent_id,
        thread_id=submission.thread_id,
        email_status=submission.email_status,
        webhook_status=submission.webhook_status,
        delivery_error=submission.delivery_error,
        sent_at=submission.sent_at,
        read_at=submission.read_at,
        deleted_at=submission.deleted_at,
        created_at=submission.created_at,
        attachments=[
            {
                "id": att.id,
                "filename": att.filename,
                "content_type": att.content_type,
                "size_bytes": att.size_bytes,
            }
            for att in resolved_attachments
        ],
    )


@router.post("", response_model=FeedbackSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: Request,
    category: str = Form(...),
    message: str = Form(...),
    subject: str | None = Form(default=None),
    submitter_name: str | None = Form(default=None),
    submitter_email: str | None = Form(default=None),
    attachments: list[UploadFile] = File(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_system_preferences(db)
    normalized_category = normalize_category(category)
    message_clean = message.strip()
    if not message_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback message cannot be empty.",
        )

    submitter_name = (
        (submitter_name or current_user.username).strip()
        if submitter_name
        else current_user.username
    )
    submitter_email = submitter_email.strip() if submitter_email else current_user.email

    submission = FeedbackSubmission(
        category=normalized_category,
        subject=subject.strip() if subject else None,
        message=message_clean,
        submitter_name=submitter_name.strip() if submitter_name else None,
        submitter_email=submitter_email.strip() if submitter_email else None,
        is_anonymous=False,
        user_id=current_user.id,
        direction="incoming",
        folder="inbox",
        is_read=False,
        email_status="pending",
        webhook_status="pending",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    if submission.thread_id is None:
        submission.thread_id = submission.id
        await db.commit()
        await db.refresh(submission)

    attachments_saved = await save_attachments(db, submission, attachments)

    email_status, email_error = await send_feedback_email(prefs, submission, attachments_saved)
    webhook_status, webhook_error = await send_feedback_webhook(
        prefs, submission, attachments_saved
    )

    submission.email_status = email_status
    submission.webhook_status = webhook_status
    submission.delivery_error = email_error or webhook_error
    submission.touch()
    await db.commit()
    await db.refresh(submission)

    await log_audit_event(
        db,
        action="feedback.submitted",
        actor=current_user,
        target_type="feedback",
        target_id=str(submission.id),
        metadata={"category": submission.category, "anonymous": submission.is_anonymous},
        request=request,
    )

    await db.refresh(submission)
    return _serialize_submission(submission, attachments_saved)


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    folder: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    prefs = await _get_system_preferences(db)
    if not prefs.feedback_store_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Feedback inbox is disabled by the administrator.",
        )
    stmt = select(FeedbackSubmission).options(selectinload(FeedbackSubmission.attachments))
    if folder:
        stmt = stmt.where(FeedbackSubmission.folder == folder)
    count_stmt = stmt.with_only_columns(FeedbackSubmission.id)
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())
    stmt = stmt.order_by(FeedbackSubmission.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return FeedbackListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[_serialize_submission(item) for item in items],
    )


@router.get("/{submission_id}/attachments/{attachment_id}")
async def download_feedback_attachment(
    submission_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    prefs = await _get_system_preferences(db)
    if not prefs.feedback_store_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Feedback inbox is disabled by the administrator.",
        )
    stmt = select(FeedbackAttachment).where(
        FeedbackAttachment.id == attachment_id,
        FeedbackAttachment.submission_id == submission_id,
    )
    result = await db.execute(stmt)
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
    return FileResponse(
        attachment.storage_path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.filename,
    )


@router.post("/{submission_id}/reply")
async def reply_to_feedback(
    submission_id: int,
    payload: FeedbackReplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    prefs = await _get_system_preferences(db)
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reply cannot be empty."
        )

    stmt = select(FeedbackSubmission).where(FeedbackSubmission.id == submission_id)
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found.")
    status_text, error = await send_feedback_reply(
        prefs,
        submission,
        message,
        reply_subject=payload.subject,
    )
    if status_text != "sent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Reply failed."
        )

    await log_audit_event(
        db,
        action="feedback.replied",
        actor=current_user,
        target_type="feedback",
        target_id=str(submission.id),
        metadata={"email": submission.submitter_email},
    )
    return {"status": "sent"}


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    prefs = await _get_system_preferences(db)
    if not prefs.feedback_store_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Feedback inbox is disabled by the administrator.",
        )

    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == submission_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found.")

    for attachment in submission.attachments:
        try:
            Path(attachment.storage_path).unlink(missing_ok=True)
        except Exception:
            pass

    await db.delete(submission)
    await db.commit()

    await log_audit_event(
        db,
        action="feedback.deleted",
        actor=current_user,
        target_type="feedback",
        target_id=str(submission_id),
    )
    return None
