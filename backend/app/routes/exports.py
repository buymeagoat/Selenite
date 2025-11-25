"""Export routes for downloading transcripts in various formats."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import json

from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.export_service import export_service

router = APIRouter(prefix="/jobs", tags=["exports"])


@router.get("/{job_id}/export")
async def export_transcript(
    job_id: str,
    format: str = "txt",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a job's transcript in the specified format.

    Args:
        job_id: Job UUID
        format: Export format (txt, srt, vtt, json, docx, md)
        current_user: Authenticated user
        db: Database session

    Returns:
        File download response with appropriate content type

    Raises:
        HTTPException: 404 if job not found, 403 if unauthorized, 400 if invalid format
    """
    # Validate format
    valid_formats = ["txt", "srt", "vtt", "json", "docx", "md"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}",
        )

    # Get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check ownership
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Check if job is completed
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed (status: {job.status}). Cannot export transcript.",
        )

    # Check if transcript exists
    if not job.transcript_path or not Path(job.transcript_path).exists():
        raise HTTPException(status_code=404, detail="Transcript file not found")

    # Read transcript text
    transcript_text = Path(job.transcript_path).read_text(encoding="utf-8")

    # Load segments if available (for formats that need them)
    segments = []
    if format in ["srt", "vtt", "json", "docx", "md"]:
        # Try to load segments from a JSON file (if Whisper saved them)
        segments_path = Path(job.transcript_path).with_suffix(".json")
        if segments_path.exists():
            try:
                transcript_data = json.loads(segments_path.read_text(encoding="utf-8"))
                segments = transcript_data.get("segments", [])
            except Exception:
                # If segments not available, continue without them
                pass

    # Generate export based on format
    try:
        if format == "txt":
            content = export_service.export_txt(job, transcript_text)
            media_type = "text/plain"
            extension = "txt"
        elif format == "srt":
            content = export_service.export_srt(job, segments)
            media_type = "text/plain"
            extension = "srt"
        elif format == "vtt":
            content = export_service.export_vtt(job, segments)
            media_type = "text/vtt"
            extension = "vtt"
        elif format == "json":
            transcript_data = {"text": transcript_text, "segments": segments}
            content = export_service.export_json(job, transcript_data)
            media_type = "application/json"
            extension = "json"
        elif format == "docx":
            content = export_service.export_docx(job, transcript_text, segments)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"
        elif format == "md":
            content = export_service.export_md(job, transcript_text, segments)
            media_type = "text/markdown"
            extension = "md"
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        # Generate filename
        base_name = Path(job.original_filename).stem
        filename = f"{base_name}.{extension}"

        # Return file response
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Export format {format} requires additional dependencies: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export transcript: {str(exc)}")
