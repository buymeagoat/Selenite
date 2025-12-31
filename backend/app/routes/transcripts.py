"""Transcript retrieval and export routes."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.job import Job
from app.models.transcript import Transcript
from app.routes.auth import get_current_user
from app.schemas.transcript import (
    TranscriptResponse,
    TranscriptSegment,
    SpeakerLabelUpdateRequest,
    SpeakerLabelsResponse,
)
from app.utils.transcript_export import (
    export_txt,
    export_md,
    export_json,
    export_srt,
    export_vtt,
    export_docx,
)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


def _resolve_transcript_path(job: Job) -> Path:
    transcript_path = None
    if job.transcript_path:
        candidate = Path(job.transcript_path)
        if candidate.exists():
            transcript_path = candidate
    if not transcript_path:
        job_id = getattr(job, "id", None)
        if job_id:
            fallback = Path(settings.transcript_storage_path) / f"{job_id}.txt"
            if fallback.exists():
                transcript_path = fallback
    if not transcript_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcript file not found."
        )
    return transcript_path


def _format_timecode(seconds: float) -> str:
    total_ms = max(seconds, 0.0) * 1000
    minutes, ms = divmod(int(total_ms), 60000)
    secs = (ms / 1000) % 60
    return f"{minutes:02d}:{secs:05.2f}"


def _format_full_text(
    segments: List[Dict[str, Any]], *, include_timestamps: bool, include_speakers: bool
) -> str:
    if not segments:
        return ""
    lines: List[str] = []
    for seg in segments:
        parts: List[str] = []
        if include_timestamps:
            parts.append(
                f"[{_format_timecode(seg.get('start', 0.0))} - "
                f"{_format_timecode(seg.get('end', 0.0))}]"
            )
        speaker = seg.get("speaker")
        if include_speakers and speaker:
            parts.append(f"{speaker}:")
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        parts.append(text)
        lines.append(" ".join(parts))
    return "\n".join(lines).strip()


def _collect_speaker_labels(segments: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    labels: List[str] = []
    for seg in segments:
        label = (seg.get("speaker") or "").strip()
        if not label or label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return labels


def _load_transcript_data(job: Job) -> Tuple[str, List[Dict[str, Any]], str, float, bool, bool]:
    """Load transcript text, segments, language and duration from disk."""
    transcript_path = _resolve_transcript_path(job)
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
                "speaker": seg.get("speaker"),
            }
        )

    return text, normalized, language, duration, has_timestamps, has_speaker_labels


def _load_transcript_metadata(path: Path) -> Dict[str, Any]:
    metadata_path = path.with_suffix(".json")
    if not metadata_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcript metadata not found."
        )
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript metadata is invalid."
        ) from exc


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


@router.get("/{job_id}/speakers", response_model=SpeakerLabelsResponse)
async def get_speaker_labels(
    job_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return available speaker labels for a completed job."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job or job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )
    if not job.has_speaker_labels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speaker labels are not available for this job.",
        )

    transcript_path = _resolve_transcript_path(job)
    metadata = _load_transcript_metadata(transcript_path)
    segments = metadata.get("segments") or []
    labels = _collect_speaker_labels(segments)
    if not labels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speaker labels are not available for this job.",
        )

    return SpeakerLabelsResponse(speakers=labels)


@router.patch("/{job_id}/speakers", response_model=SpeakerLabelsResponse)
async def update_speaker_labels(
    job_id: UUID,
    payload: SpeakerLabelUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename speaker labels for a completed job transcript."""
    result = await db.execute(
        select(Job).where(Job.id == str(job_id), Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job or job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found. Job may not be completed.",
        )
    if not job.has_speaker_labels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speaker labels are not available for this job.",
        )

    updates = {item.label.strip(): item.name.strip() for item in payload.updates}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No speaker updates provided."
        )

    transcript_path = _resolve_transcript_path(job)
    metadata = _load_transcript_metadata(transcript_path)
    segments = metadata.get("segments") or []
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speaker labels are not available for this job.",
        )

    for seg in segments:
        speaker = seg.get("speaker")
        if not speaker:
            continue
        speaker_value = str(speaker)
        if speaker_value in updates:
            seg["speaker"] = updates[speaker_value]

    has_timestamps = bool((metadata.get("options") or {}).get("has_timestamps", job.has_timestamps))
    include_speakers = bool(
        (metadata.get("options") or {}).get("has_speaker_labels", job.has_speaker_labels)
    )
    text = _format_full_text(
        segments, include_timestamps=has_timestamps, include_speakers=include_speakers
    )

    metadata["segments"] = segments
    metadata["text"] = text
    metadata_path = transcript_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    transcript_path.write_text(text, encoding="utf-8")

    result = await db.execute(
        select(Transcript).where(Transcript.job_id == str(job.id), Transcript.format == "txt")
    )
    transcript_record = result.scalar_one_or_none()
    if transcript_record:
        transcript_record.file_size = transcript_path.stat().st_size

    job.updated_at = datetime.utcnow()
    await db.commit()

    labels = _collect_speaker_labels(segments)
    return SpeakerLabelsResponse(speakers=labels)


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
