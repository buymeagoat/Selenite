"""Transcript retrieval and export routes."""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
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


def _load_transcript_data(job: Job) -> Tuple[str, List[Dict[str, Any]], str, float, bool, bool]:
    """Load transcript text, segments, language and duration from disk."""
    if not job.transcript_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcript file not found."
        )

    transcript_path = Path(job.transcript_path)
    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcript file not found."
        )

    text = transcript_path.read_text(encoding="utf-8").strip()
    language = job.language_detected or "unknown"
    duration = job.duration or 0.0
    segments: List[Dict[str, Any]] = []
    has_timestamps = bool(job.has_timestamps)
    has_speaker_labels = bool(job.has_speaker_labels)

    metadata_path = transcript_path.with_suffix(".json")
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            segments = metadata.get("segments") or []
            language = metadata.get("language") or language
            duration = metadata.get("duration") or duration
            options = metadata.get("options") or {}
            has_timestamps = bool(options.get("has_timestamps", has_timestamps))
            has_speaker_labels = bool(options.get("has_speaker_labels", has_speaker_labels))
            if not text and metadata.get("text"):
                text = metadata["text"]
        except json.JSONDecodeError:
            pass

    if not segments:
        segments = [{"id": 0, "start": 0.0, "end": duration, "text": text}]

    normalized: List[Dict[str, Any]] = []
    for idx, seg in enumerate(segments):
        normalized.append(
            {
                "id": seg.get("id", idx),
                "start": float(seg.get("start", 0.0) or 0.0),
                "end": float(seg.get("end", 0.0) or 0.0),
                "text": (seg.get("text") or "").strip(),
            }
        )

    return text, normalized, language, duration, has_timestamps, has_speaker_labels


@router.get("/{job_id}", response_model=TranscriptResponse)
async def get_transcript(
    job_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the primary transcript structure for a completed job."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job or job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    (
        text,
        segments,
        language,
        duration,
        has_timestamps,
        has_speaker_labels,
    ) = _load_transcript_data(job)

    return TranscriptResponse(
        job_id=str(job.id),
        text=text,
        segments=[TranscriptSegment(**seg) for seg in segments],
        language=language,
        duration=duration,
        has_timestamps=has_timestamps,
        has_speaker_labels=has_speaker_labels,
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
    if not job or job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )

    text, segments, language, duration, _, _ = _load_transcript_data(job)
    title = Path(job.original_filename).stem

    if fmt == "txt":
        content, content_type = export_txt(text)
    elif fmt == "md":
        content, content_type = export_md(title, text)
    elif fmt == "srt":
        content, content_type = export_srt(segments)
    elif fmt == "vtt":
        content, content_type = export_vtt(segments)
    elif fmt == "json":
        payload = {
            "job_id": str(job.id),
            "text": text,
            "segments": segments,
            "language": language,
            "duration": duration,
        }
        content, content_type = export_json(payload)
    elif fmt == "docx":
        content, content_type = export_docx(title, segments, {"language": language})
    else:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format")

    filename = f"{title}.{fmt}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=content, media_type=content_type, headers=headers)
