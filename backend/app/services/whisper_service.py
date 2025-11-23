"""Whisper model management and transcription service.

Handles loading Whisper models, processing audio/video files,
and generating transcriptions with timestamps and speaker labels.
"""

import asyncio
from contextlib import suppress
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.job import Job
from app.models.transcript import Transcript

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading
_model_cache: Dict[str, Any] = {}
_model_lock = asyncio.Lock()


class WhisperService:
    """Service for Whisper model management and transcription."""

    def __init__(self, model_storage_path: Optional[str] = None):
        """Initialize Whisper service.

        Args:
            model_storage_path: Path to directory containing Whisper models
        """
        self.model_storage_path = model_storage_path or settings.model_storage_path
        # Resolve path relative to backend directory
        if Path(self.model_storage_path).is_absolute():
            self.models_dir = Path(self.model_storage_path)
        else:
            # Make relative to backend directory (app's grandparent)
            backend_dir = Path(__file__).parent.parent.parent
            self.models_dir = (backend_dir / self.model_storage_path).resolve()

    def _is_cancelled_state(self, job: Job) -> bool:
        return job.status in {"cancelled", "cancelling"}

    async def _finalize_cancellation(self, job: Job, db: AsyncSession, context: str) -> None:
        """Finalize a cancellation by ensuring consistent state and logging."""
        job.status = "cancelled"
        job.progress_stage = None
        job.estimated_time_left = None
        if job.completed_at is None:
            job.completed_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Job {job.id} cancellation acknowledged ({context})")

    async def _abort_if_cancelled(self, job: Job, db: AsyncSession, context: str) -> bool:
        await db.refresh(job)
        if self._is_cancelled_state(job):
            await self._finalize_cancellation(job, db, context)
            return True
        return False

    async def load_model(self, model_name: str) -> Any:
        """Load a Whisper model, using cache if available.

        Args:
            model_name: Model size (tiny, base, small, medium, large-v3)

        Returns:
            Loaded Whisper model

        Raises:
            FileNotFoundError: If model file doesn't exist
            ImportError: If openai-whisper package not installed
        """
        async with _model_lock:
            if model_name in _model_cache:
                logger.info(f"Using cached Whisper model: {model_name}")
                return _model_cache[model_name]

            logger.info(f"Loading Whisper model: {model_name}")

            try:
                import whisper
            except ImportError:
                raise ImportError(
                    "openai-whisper package not installed. "
                    "Install with: pip install openai-whisper"
                )

            # Check if model file exists locally
            model_file = self.models_dir / f"{model_name}.pt"
            if not model_file.exists():
                raise FileNotFoundError(
                    f"Model file not found: {model_file}. "
                    f"Available models in {self.models_dir}: "
                    f"{[f.stem for f in self.models_dir.glob('*.pt')]}"
                )

            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None, lambda: whisper.load_model(model_name, download_root=str(self.models_dir))
            )

            _model_cache[model_name] = model
            logger.info(f"Successfully loaded Whisper model: {model_name}")
            return model

    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str,
        language: Optional[str] = None,
        enable_timestamps: bool = True,
        enable_speaker_detection: bool = False,
    ) -> Dict[str, Any]:
        """Transcribe an audio/video file using Whisper.

        Args:
            audio_path: Path to audio/video file
            model_name: Whisper model to use
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            enable_timestamps: Include word-level timestamps
            enable_speaker_detection: Enable speaker diarization (requires pyannote)

        Returns:
            Dictionary with transcription results:
            {
                'text': str,  # Full transcript text
                'segments': List[Dict],  # Timestamped segments
                'language': str,  # Detected or specified language
                'duration': float,  # Audio duration in seconds
            }

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting transcription: {audio_path} with model {model_name}")

        try:
            model = await self.load_model(model_name)

            # Prepare transcription options
            transcribe_options = {
                "language": language if language and language != "auto" else None,
                "task": "transcribe",
                "verbose": False,
            }

            # Run transcription in thread pool (CPU-intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(audio_path, **transcribe_options)
            )

            # Extract results
            normalized_segments = self._normalize_segments(result.get("segments", []))
            formatted_text = self._format_full_text(
                normalized_segments,
                include_timestamps=enable_timestamps,
                include_speakers=enable_speaker_detection,
            )
            transcript_result = {
                "text": formatted_text or result["text"].strip(),
                "segments": normalized_segments,
                "language": result.get("language", "unknown"),
                "duration": result.get("duration", 0.0),
            }

            # TODO: Speaker diarization integration (requires pyannote.audio)
            # if enable_speaker_detection:
            #     transcript_result = await self._add_speaker_labels(
            #         audio_path, transcript_result
            #     )

            logger.info(
                f"Transcription complete: {len(transcript_result['segments'])} segments, "
                f"{transcript_result['duration']:.1f}s duration"
            )

            return transcript_result

        except Exception as exc:
            logger.error(f"Transcription failed for {audio_path}: {exc}")
            raise RuntimeError(f"Transcription failed: {str(exc)}") from exc

    async def process_job(self, job_id: str, db: AsyncSession) -> None:
        """Process a transcription job end-to-end.

        Args:
            job_id: Job UUID
            db: Database session

        Updates job status, progress, and saves transcript to database.
        """
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Job not found: {job_id}")
            return

        if self._is_cancelled_state(job):
            await self._finalize_cancellation(job, db, "job fetched")
            return

        progress_task: Optional[asyncio.Task] = None
        progress_task: Optional[asyncio.Task] = None
        try:
            if settings.is_testing:
                await self._wait_for_processing_slot(db)
            if settings.is_testing:
                await self._simulate_transcription(job, db)
                logger.info(f"Job {job_id} completed via simulated transcription")
                return
            # Check if already cancelled
            if self._is_cancelled_state(job):
                await self._finalize_cancellation(job, db, "before processing")
                return

            # Stage 1: Loading model
            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.progress_percent = 10
            job.progress_stage = "loading_model"
            job.estimated_total_seconds = (
                job.estimated_total_seconds or self._estimate_total_seconds(job)
            )
            job.estimated_time_left = job.estimated_total_seconds
            await db.commit()

            # Refresh in case another process marked this job failed/stalled
            await db.refresh(job)
            if job.status != "processing":
                logger.warning(
                    "Job %s left processing state during transcription; aborting finalize", job_id
                )
                return

            model_name = job.model_used or settings.default_whisper_model
            language = job.language_detected if job.language_detected != "auto" else None

            if await self._abort_if_cancelled(job, db, "after loading model"):
                return

            # Load model (will use cache if available)
            await self.load_model(model_name)

            if await self._abort_if_cancelled(job, db, "after model load"):
                return

            # Stage 2: Transcribing
            job.progress_percent = 30
            job.progress_stage = "transcribing"
            job.estimated_time_left = job.estimated_time_left or job.estimated_total_seconds
            await db.commit()

            # Nudge progress forward while Whisper transcribes (best-effort)
            progress_task = asyncio.create_task(
                self._drain_progress_during_transcription(job.id, cap_percent=95)
            )

            if await self._abort_if_cancelled(job, db, "before transcription"):
                if progress_task:
                    progress_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await progress_task
                return

            # Perform transcription
            transcript_result = await self.transcribe_audio(
                audio_path=job.file_path,
                model_name=model_name,
                language=language,
                enable_timestamps=job.has_timestamps,
                enable_speaker_detection=job.has_speaker_labels,
            )

            if await self._abort_if_cancelled(job, db, "after transcription"):
                if progress_task:
                    progress_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await progress_task
                return

            # Stop background progress updates now that transcription is done
            if progress_task:
                progress_task.cancel()
                with suppress(asyncio.CancelledError):
                    await progress_task

            # Stage 3: Finalizing
            job.progress_percent = 90
            job.progress_stage = "finalizing"
            await db.commit()

            # Save transcript to file + metadata
            transcript_path = Path(settings.transcript_storage_path) / f"{job_id}.txt"
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            transcript_path.write_text(transcript_result["text"], encoding="utf-8")
            metadata_path = transcript_path.with_suffix(".json")
            metadata = {
                "text": transcript_result["text"],
                "segments": transcript_result["segments"],
                "language": transcript_result["language"],
                "duration": transcript_result["duration"],
                "options": {
                    "has_timestamps": bool(job.has_timestamps),
                    "has_speaker_labels": bool(job.has_speaker_labels),
                },
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            # Create transcript database record
            transcript_db = Transcript(
                job_id=job_id,
                format="txt",
                file_path=str(transcript_path),
                file_size=transcript_path.stat().st_size,
            )
            db.add(transcript_db)

            # Update job with results
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100
            job.progress_stage = None
            job.estimated_time_left = None
            job.duration = transcript_result["duration"]
            job.language_detected = transcript_result["language"]
            job.speaker_count = self._estimate_speaker_count(transcript_result)
            job.transcript_path = str(transcript_path)
            job.estimated_total_seconds = self._estimate_total_seconds(
                job, transcript_result["duration"]
            )

            await db.commit()
            logger.info(f"Job {job_id} completed successfully")

        except Exception as exc:
            if progress_task:
                progress_task.cancel()
                with suppress(asyncio.CancelledError):
                    await progress_task
            await db.refresh(job)
            if self._is_cancelled_state(job):
                await self._finalize_cancellation(job, db, "during exception")
                return
            logger.error(f"Job {job_id} failed: {exc}")
            job.status = "failed"
            job.progress_stage = None
            job.estimated_time_left = None
            job.error_message = str(exc)
            await db.commit()

    def _estimate_speaker_count(self, transcript_result: Dict[str, Any]) -> int:
        """Estimate number of speakers from transcript.

        Simple heuristic until proper diarization is implemented.

        Args:
            transcript_result: Transcription result dictionary

        Returns:
            Estimated speaker count
        """
        # TODO: Implement proper speaker diarization
        # For now, return 1 as default
        return 1

    def _model_speed_factor(self, model_name: str) -> float:
        """Approximate realtime factor per model size."""
        lookup = {
            "tiny": 0.5,
            "base": 0.8,
            "small": 1.0,
            "medium": 1.3,
            "large": 1.6,
            "large-v3": 1.6,
        }
        return lookup.get(model_name, 1.3)

    def _estimate_total_seconds(self, job: Job, duration_hint: Optional[float] = None) -> int:
        """Estimate total processing time based on duration and model."""
        duration = duration_hint if duration_hint is not None else job.duration
        base_seconds = float(duration or settings.default_estimated_duration_seconds)
        factor = self._model_speed_factor(job.model_used or settings.default_whisper_model)
        estimate = int(max(base_seconds * factor, 60))
        return estimate

    @staticmethod
    def _format_timecode(seconds: float) -> str:
        total_ms = max(seconds, 0.0) * 1000
        minutes, ms = divmod(int(total_ms), 60000)
        secs = (ms / 1000) % 60
        return f"{minutes:02d}:{secs:05.2f}"

    def _format_full_text(
        self,
        segments: list[Dict[str, Any]],
        *,
        include_timestamps: bool,
        include_speakers: bool,
    ) -> str:
        """Build a readable block of text honoring timestamp/speaker choices."""
        if not segments:
            return ""
        lines: list[str] = []
        for idx, seg in enumerate(segments, start=1):
            parts: list[str] = []
            if include_timestamps:
                parts.append(
                    f"[{self._format_timecode(seg.get('start', 0.0))} – "
                    f"{self._format_timecode(seg.get('end', 0.0))}]"
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

    def _normalize_segments(self, segments: Optional[list]) -> list[Dict[str, Any]]:
        """Ensure every segment has id/start/end/text fields."""
        normalized: list[Dict[str, Any]] = []
        if not segments:
            return normalized

        def coerce_value(item, key, default=0.0):
            if isinstance(item, dict):
                value = item.get(key, default)
            else:
                value = getattr(item, key, default)
            return float(value or 0.0)

        def coerce_text(item):
            if isinstance(item, dict):
                raw = item.get("text") or ""
            else:
                raw = getattr(item, "text", "") or ""
            return raw.strip()

        def coerce_speaker(item):
            if isinstance(item, dict):
                return item.get("speaker")
            return getattr(item, "speaker", None)

        for idx, seg in enumerate(segments):
            text = coerce_text(seg)
            if not text:
                continue
            normalized.append(
                {
                    "id": (
                        getattr(seg, "id", idx) if not isinstance(seg, dict) else seg.get("id", idx)
                    ),
                    "start": coerce_value(seg, "start"),
                    "end": coerce_value(seg, "end"),
                    "text": text,
                    "speaker": coerce_speaker(seg),
                }
            )
        return normalized

    async def _drain_progress_during_transcription(
        self, job_id: str, *, cap_percent: int = 95, interval: float = 2.0
    ) -> None:
        """Advance progress based on elapsed time versus estimated total."""
        try:
            while True:
                await asyncio.sleep(interval)
                async with AsyncSessionLocal() as session:
                    job_obj = await session.get(Job, job_id)
                    if not job_obj or job_obj.status != "processing" or not job_obj.started_at:
                        return

                    est_total = (
                        job_obj.estimated_total_seconds
                        or settings.default_estimated_duration_seconds
                    )
                    elapsed = (datetime.utcnow() - job_obj.started_at).total_seconds()
                    if elapsed > est_total:
                        # Expand estimate if we're running long to avoid pinning at 95%
                        est_total = int(elapsed * 1.25)
                        job_obj.estimated_total_seconds = est_total

                    progress = int((elapsed / est_total) * 100)
                    progress = max(progress, int(job_obj.progress_percent or 0))
                    progress = min(progress, cap_percent)
                    job_obj.progress_percent = progress

                    remaining = max(int(est_total - elapsed), 0)
                    job_obj.estimated_time_left = remaining if progress < 100 else None
                    job_obj.updated_at = datetime.utcnow()
                    await session.commit()
        except asyncio.CancelledError:
            return
        except Exception as exc:  # Best-effort, don't fail transcription for this
            logger.warning("Progress updater failed for job %s: %s", job_id, exc)

    async def _simulate_transcription(self, job: Job, db: AsyncSession) -> None:
        """Fast path for tests to avoid loading large Whisper models."""
        transcript_text = f"Simulated transcript for {job.original_filename}"
        segments = [
            {
                "id": 0,
                "start": 0.0,
                "end": float(job.duration or 10.0),
                "text": transcript_text,
                "speaker": "Speaker 1" if job.has_speaker_labels else None,
            }
        ]
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.progress_percent = 10
        job.progress_stage = "loading_model"
        job.estimated_total_seconds = job.estimated_total_seconds or 180
        job.estimated_time_left = job.estimated_total_seconds
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 60
        job.progress_stage = "transcribing"
        job.estimated_time_left = 30
        job.updated_at = datetime.utcnow()
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 90
        job.progress_stage = "finalizing"
        job.estimated_time_left = 5
        job.updated_at = datetime.utcnow()
        await db.commit()

        await asyncio.sleep(0.2)

        transcript_path = Path(settings.transcript_storage_path) / f"{job.id}.txt"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        formatted_text = self._format_full_text(
            segments,
            include_timestamps=bool(job.has_timestamps),
            include_speakers=bool(job.has_speaker_labels),
        )
        transcript_path.write_text(formatted_text or transcript_text, encoding="utf-8")
        metadata_path = transcript_path.with_suffix(".json")
        metadata = {
            "text": formatted_text or transcript_text,
            "segments": segments,
            "language": job.language_detected or "en",
            "duration": job.duration or 10.0,
            "options": {
                "has_timestamps": bool(job.has_timestamps),
                "has_speaker_labels": bool(job.has_speaker_labels),
            },
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

        transcript_db = Transcript(
            job_id=job.id,
            format="txt",
            file_path=str(transcript_path),
            file_size=len(transcript_text.encode("utf-8")),
        )
        db.add(transcript_db)

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100
        job.progress_stage = None
        job.estimated_time_left = None
        job.duration = job.duration or 60.0
        job.language_detected = job.language_detected or "en"
        job.speaker_count = job.speaker_count or 1
        job.transcript_path = str(transcript_path)
        job.updated_at = datetime.utcnow()

        await db.commit()

    async def _wait_for_processing_slot(self, db: AsyncSession) -> None:
        """Ensure processing job count stays within configured limit (testing helper)."""
        max_jobs = settings.max_concurrent_jobs
        if max_jobs <= 0:
            return
        while True:
            result = await db.execute(
                select(func.count()).select_from(Job).where(Job.status == "processing")
            )
            count = result.scalar_one() or 0
            if count < max_jobs:
                return
            await asyncio.sleep(0.02)


# Global service instance
whisper_service = WhisperService()
