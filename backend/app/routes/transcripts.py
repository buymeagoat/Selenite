"""Transcript retrieval and export routes."""

from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.routes.auth import get_current_user
from app.schemas.transcript import TranscriptResponse, TranscriptSegment
from app.utils.transcript_export import (
    export_txt,
    export_md,
    export_json,
    export_srt,
    export_vtt,
    export_docx,
)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


def _synthesized_segments() -> List[Dict[str, Any]]:
    """Create a minimal set of segments for the simulated transcript."""
    return [
        {"id": 0, "start": 0.0, "end": 5.0, "text": "Hello, this is a simulated transcript."},
        {"id": 1, "start": 5.0, "end": 12.5, "text": "It demonstrates export formats for testing."},
        {"id": 2, "start": 12.5, "end": 18.0, "text": "Thank you for trying Selenite."},
    ]


@router.get("/{job_id}", response_model=TranscriptResponse)
async def get_transcript(
    job_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the primary transcript structure for a completed job.

    In Increment 6, content is synthesized to enable export functionality.
    """
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    segments = _synthesized_segments()
    full_text = " ".join(seg["text"] for seg in segments)
    language = job.language_detected or "en"
    duration = job.duration or 60.0

    return TranscriptResponse(
        job_id=str(job.id),
        text=full_text,
        segments=[TranscriptSegment(**seg) for seg in segments],
        language=language,
        duration=duration,
    )


@router.get("/{job_id}/export")
async def export_transcript(
    job_id: UUID,
    format: str = Query(..., description="Export format (txt, md, srt, vtt, json, docx)"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export transcript in the requested format for a completed job."""
    fmt = (format or "").lower()
    allowed = {"txt", "md", "srt", "vtt", "json", "docx"}
    if fmt not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Supported: txt, md, srt, vtt, json, docx",
        )

    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    # Build synthesized transcript
    segments = _synthesized_segments()
    full_text = "\n".join(seg["text"] for seg in segments)
    language = job.language_detected or "en"
    duration = job.duration or 60.0

    title = Path(job.original_filename).stem

    if fmt == "txt":
        content, content_type = export_txt(full_text)
    elif fmt == "md":
        content, content_type = export_md(title, full_text)
    elif fmt == "srt":
        content, content_type = export_srt(segments)
    elif fmt == "vtt":
        content, content_type = export_vtt(segments)
    elif fmt == "json":
        payload = {
            "job_id": str(job.id),
            "text": full_text,
            "segments": segments,
            "language": language,
            "duration": duration,
        }
        content, content_type = export_json(payload)
    elif fmt == "docx":
        content, content_type = export_docx(title, segments, {"language": language})
    else:  # pragma: no cover - defensive, should not happen due to earlier check
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format")

    filename = f"{title}-transcript.{fmt}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(content=content, media_type=content_type, headers=headers)
