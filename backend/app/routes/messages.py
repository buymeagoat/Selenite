"""Admin message inbox routes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    Query,
    status,
    Request,
)
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.feedback import FeedbackSubmission, FeedbackAttachment
from app.models.system_preferences import SystemPreferences
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.feedback import (
    FeedbackSubmissionResponse,
    FeedbackListResponse,
    FeedbackDetailResponse,
)
from app.services.feedback import save_attachments, send_feedback_reply, send_outbound_message
from app.services.audit import log_audit_event


router = APIRouter(prefix="/messages", tags=["messages"])

FOLDER_VALUES = {"inbox", "archived", "sent", "deleted", "drafts"}
OUTGOING_FOLDERS = {"sent", "drafts"}


def _ensure_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")


async def _get_system_preferences(db: AsyncSession) -> SystemPreferences:
    result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = SystemPreferences(id=1)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


def _normalize_folder(folder: str) -> str:
    normalized = folder.strip().lower()
    if normalized not in FOLDER_VALUES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid folder.")
    return normalized


def _serialize_message(
    submission: FeedbackSubmission,
    attachments: list[FeedbackAttachment] | None = None,
) -> FeedbackSubmissionResponse:
    from app.routes.feedback import _serialize_submission

    return _serialize_submission(submission, attachments)


@router.get("", response_model=FeedbackListResponse)
async def list_messages(
    folder: str = Query(default="inbox"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    folder_value = _normalize_folder(folder)

    stmt = select(FeedbackSubmission).options(selectinload(FeedbackSubmission.attachments))
    stmt = stmt.where(FeedbackSubmission.folder == folder_value)
    if unread_only:
        stmt = stmt.where(FeedbackSubmission.is_read.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                FeedbackSubmission.subject.ilike(pattern),
                FeedbackSubmission.message.ilike(pattern),
                FeedbackSubmission.submitter_name.ilike(pattern),
                FeedbackSubmission.submitter_email.ilike(pattern),
                FeedbackSubmission.recipient_email.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)
    result = await db.execute(
        stmt.order_by(FeedbackSubmission.created_at.desc()).offset(offset).limit(limit)
    )
    items = result.scalars().all()
    return FeedbackListResponse(
        total=total or 0,
        limit=limit,
        offset=offset,
        items=[_serialize_message(item) for item in items],
    )


@router.get("/{message_id}", response_model=FeedbackDetailResponse)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread_id = message.thread_id or message.id
    thread_stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.thread_id == thread_id)
        .order_by(FeedbackSubmission.created_at.asc())
    )
    thread_result = await db.execute(thread_stmt)
    thread_items = thread_result.scalars().all()
    return FeedbackDetailResponse(
        message=_serialize_message(message),
        thread=[_serialize_message(item) for item in thread_items],
    )


@router.post("/drafts", response_model=FeedbackSubmissionResponse)
async def create_draft(
    request: Request,
    subject: str | None = Form(default=None),
    message: str | None = Form(default=None),
    recipient_email: str | None = Form(default=None),
    parent_id: int | None = Form(default=None),
    attachments: list[UploadFile] = File(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    if not subject and not (message or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Draft must include a subject or body."
        )

    thread_id = None
    if parent_id:
        parent_stmt = select(FeedbackSubmission).where(FeedbackSubmission.id == parent_id)
        parent_result = await db.execute(parent_stmt)
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent message not found."
            )
        thread_id = parent.thread_id or parent.id

    submission = FeedbackSubmission(
        category="comment",
        subject=subject.strip() if subject else None,
        message=message.strip() if message else "",
        submitter_name=None,
        submitter_email=None,
        recipient_email=recipient_email.strip() if recipient_email else None,
        is_anonymous=False,
        user_id=None,
        sender_user_id=current_user.id,
        direction="outgoing",
        folder="drafts",
        is_read=True,
        parent_id=parent_id,
        thread_id=thread_id,
        email_status="draft",
        webhook_status="skipped",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    if submission.thread_id is None:
        submission.thread_id = submission.id
        await db.commit()
        await db.refresh(submission)

    attachments_saved = await save_attachments(db, submission, attachments)
    await log_audit_event(
        db,
        action="message.draft_created",
        actor=current_user,
        target_type="message",
        target_id=str(submission.id),
        request=request,
    )
    return _serialize_message(submission, attachments_saved)


@router.patch("/drafts/{message_id}", response_model=FeedbackSubmissionResponse)
async def update_draft(
    message_id: int,
    request: Request,
    subject: str | None = Form(default=None),
    message: str | None = Form(default=None),
    recipient_email: str | None = Form(default=None),
    parent_id: int | None = Form(default=None),
    attachments: list[UploadFile] = File(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")
    if submission.folder != "drafts":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message is not a draft."
        )

    if subject is not None:
        submission.subject = subject.strip() or None
    if message is not None:
        submission.message = message.strip()
    if recipient_email is not None:
        submission.recipient_email = recipient_email.strip() or None
    if parent_id is not None:
        parent_stmt = select(FeedbackSubmission).where(FeedbackSubmission.id == parent_id)
        parent_result = await db.execute(parent_stmt)
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent message not found."
            )
        submission.parent_id = parent_id
        submission.thread_id = parent.thread_id or parent.id
    submission.touch()
    await db.commit()
    await db.refresh(submission)

    attachments_saved = await save_attachments(db, submission, attachments)
    await log_audit_event(
        db,
        action="message.draft_updated",
        actor=current_user,
        target_type="message",
        target_id=str(submission.id),
        request=request,
    )
    if attachments_saved:
        return _serialize_message(submission, attachments_saved)
    submission = await _load_submission_with_attachments(db, message_id)
    return _serialize_message(submission)


@router.post("/drafts/{message_id}/send", response_model=FeedbackSubmissionResponse)
async def send_draft(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    prefs = await _get_system_preferences(db)
    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found.")
    if submission.folder != "drafts":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message is not a draft."
        )
    if not submission.recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient email is required."
        )

    status_text, error = await send_outbound_message(
        prefs,
        submission.recipient_email,
        submission.subject,
        submission.message,
        submission.attachments,
    )
    if status_text != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Send failed.")

    submission.folder = "sent"
    submission.email_status = "sent"
    submission.sent_at = datetime.utcnow()
    submission.touch()
    await db.commit()
    await db.refresh(submission)
    await log_audit_event(
        db,
        action="message.draft_sent",
        actor=current_user,
        target_type="message",
        target_id=str(submission.id),
        request=request,
    )
    submission = await _load_submission_with_attachments(db, message_id)
    return _serialize_message(submission)


@router.post("/send", response_model=FeedbackSubmissionResponse)
async def send_message(
    request: Request,
    recipient_email: str = Form(...),
    subject: str | None = Form(default=None),
    message: str = Form(...),
    attachments: list[UploadFile] = File(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    prefs = await _get_system_preferences(db)
    body = message.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message body cannot be empty."
        )

    submission = FeedbackSubmission(
        category="comment",
        subject=subject.strip() if subject else None,
        message=body,
        recipient_email=recipient_email.strip(),
        is_anonymous=False,
        sender_user_id=current_user.id,
        direction="outgoing",
        folder="sent",
        is_read=True,
        email_status="pending",
        webhook_status="skipped",
        sent_at=datetime.utcnow(),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    submission.thread_id = submission.id
    await db.commit()
    await db.refresh(submission)

    attachments_saved = await save_attachments(db, submission, attachments)
    status_text, error = await send_outbound_message(
        prefs,
        submission.recipient_email or "",
        submission.subject,
        submission.message,
        attachments_saved,
    )
    if status_text != "sent":
        submission.email_status = "failed"
        submission.delivery_error = error
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Send failed.")

    submission.email_status = "sent"
    submission.touch()
    await db.commit()
    await db.refresh(submission)
    await log_audit_event(
        db,
        action="message.sent",
        actor=current_user,
        target_type="message",
        target_id=str(submission.id),
        request=request,
    )
    return _serialize_message(submission, attachments_saved)


@router.post("/{message_id}/reply", response_model=FeedbackSubmissionResponse)
async def reply_message(
    message_id: int,
    request: Request,
    message: str = Form(...),
    subject: str | None = Form(default=None),
    attachments: list[UploadFile] = File(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    prefs = await _get_system_preferences(db)
    body = message.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reply cannot be empty."
        )

    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if not original.submitter_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No submitter email on this message."
        )

    thread_id = original.thread_id or original.id
    submission = FeedbackSubmission(
        category=original.category,
        subject=subject.strip() if subject else original.subject,
        message=body,
        recipient_email=original.submitter_email,
        is_anonymous=False,
        sender_user_id=current_user.id,
        direction="outgoing",
        folder="sent",
        is_read=True,
        parent_id=original.id,
        thread_id=thread_id,
        email_status="pending",
        webhook_status="skipped",
        sent_at=datetime.utcnow(),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    attachments_saved = await save_attachments(db, submission, attachments)
    status_text, error = await send_feedback_reply(
        prefs,
        original,
        body,
        reply_subject=submission.subject,
        attachments=attachments_saved,
    )
    if status_text != "sent":
        submission.email_status = "failed"
        submission.delivery_error = error
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Reply failed."
        )

    submission.email_status = "sent"
    submission.touch()
    await db.commit()
    await db.refresh(submission)
    await log_audit_event(
        db,
        action="message.replied",
        actor=current_user,
        target_type="message",
        target_id=str(submission.id),
        request=request,
    )
    return _serialize_message(submission, attachments_saved)


@router.post("/{message_id}/archive")
async def archive_message(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_folder(db, message_id, "archived")
    await log_audit_event(
        db,
        action="message.archived",
        actor=current_user,
        target_type="message",
        target_id=str(message_id),
        request=request,
    )
    return _serialize_message(submission)


@router.post("/{message_id}/unarchive")
async def unarchive_message(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_folder(db, message_id, "inbox", clear_deleted=True)
    await log_audit_event(
        db,
        action="message.unarchived",
        actor=current_user,
        target_type="message",
        target_id=str(message_id),
        request=request,
    )
    return _serialize_message(submission)


@router.post("/{message_id}/delete")
async def delete_message(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_folder(db, message_id, "deleted", deleted=True)
    await log_audit_event(
        db,
        action="message.deleted",
        actor=current_user,
        target_type="message",
        target_id=str(message_id),
        request=request,
    )
    return _serialize_message(submission)


@router.post("/{message_id}/restore")
async def restore_message(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_folder(db, message_id, "inbox", clear_deleted=True)
    await log_audit_event(
        db,
        action="message.restored",
        actor=current_user,
        target_type="message",
        target_id=str(message_id),
        request=request,
    )
    return _serialize_message(submission)


@router.delete("/{message_id}")
async def purge_message(
    message_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    await _purge_message(db, message_id)
    await log_audit_event(
        db,
        action="message.purged",
        actor=current_user,
        target_type="message",
        target_id=str(message_id),
        request=request,
    )
    return {"status": "purged"}


@router.post("/{message_id}/read")
async def mark_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_read_state(db, message_id, True)
    return _serialize_message(submission)


@router.post("/{message_id}/unread")
async def mark_unread(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    submission = await _set_read_state(db, message_id, False)
    return _serialize_message(submission)


@router.post("/bulk")
async def bulk_action(
    action: str = Form(...),
    ids: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_admin(current_user)
    action_value = action.strip().lower()
    try:
        id_list = [int(item) for item in ids.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid message id list."
        ) from exc
    if not id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No message ids provided."
        )

    if action_value == "archive":
        for message_id in id_list:
            await _set_folder(db, message_id, "archived")
    elif action_value == "delete":
        for message_id in id_list:
            await _set_folder(db, message_id, "deleted", deleted=True)
    elif action_value == "restore":
        for message_id in id_list:
            await _set_folder(db, message_id, "inbox", clear_deleted=True)
    elif action_value == "purge":
        for message_id in id_list:
            await _purge_message(db, message_id)
    elif action_value == "read":
        for message_id in id_list:
            await _set_read_state(db, message_id, True)
    elif action_value == "unread":
        for message_id in id_list:
            await _set_read_state(db, message_id, False)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bulk action.")

    await log_audit_event(
        db,
        action="message.bulk_action",
        actor=current_user,
        target_type="message",
        target_id=",".join(str(item) for item in id_list),
        metadata={"action": action_value},
    )
    return {"status": "ok"}


async def _set_folder(
    db: AsyncSession,
    message_id: int,
    folder: str,
    *,
    deleted: bool = False,
    clear_deleted: bool = False,
) -> FeedbackSubmission:
    stmt = select(FeedbackSubmission).where(FeedbackSubmission.id == message_id)
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    submission.folder = folder
    if deleted:
        submission.deleted_at = datetime.utcnow()
    if clear_deleted:
        submission.deleted_at = None
    submission.touch()
    await db.commit()
    return await _load_submission_with_attachments(db, message_id)


async def _set_read_state(
    db: AsyncSession,
    message_id: int,
    is_read: bool,
) -> FeedbackSubmission:
    stmt = select(FeedbackSubmission).where(FeedbackSubmission.id == message_id)
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    submission.is_read = is_read
    submission.read_at = datetime.utcnow() if is_read else None
    submission.touch()
    await db.commit()
    return await _load_submission_with_attachments(db, message_id)


async def _load_submission_with_attachments(
    db: AsyncSession,
    message_id: int,
) -> FeedbackSubmission:
    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    return submission


async def _purge_message(db: AsyncSession, message_id: int) -> None:
    stmt = (
        select(FeedbackSubmission)
        .options(selectinload(FeedbackSubmission.attachments))
        .where(FeedbackSubmission.id == message_id)
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    for attachment in submission.attachments:
        try:
            Path(attachment.storage_path).unlink(missing_ok=True)
        except Exception:
            pass
    await db.delete(submission)
    await db.commit()
