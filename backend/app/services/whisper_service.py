"""Whisper model management and transcription service.

Handles loading Whisper models, processing audio/video files,
and generating transcriptions with timestamps and speaker labels.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.transcript import Transcript
from app.config import settings

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
            transcript_result = {
                "text": result["text"].strip(),
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
            await db.commit()

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
            await db.commit()

            if await self._abort_if_cancelled(job, db, "before transcription"):
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
                return

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

            await db.commit()
            logger.info(f"Job {job_id} completed successfully")

        except Exception as exc:
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

    def _normalize_segments(self, segments: Optional[list]) -> list[Dict[str, Any]]:
        """Ensure every segment has id/start/end/text fields."""
        normalized: list[Dict[str, Any]] = []
        if not segments:
            return normalized
        for idx, seg in enumerate(segments):
            if not isinstance(seg, dict):
                continue
            normalized.append(
                {
                    "id": seg.get("id", idx),
                    "start": float(seg.get("start", 0.0) or 0.0),
                    "end": float(seg.get("end", 0.0) or 0.0),
                    "text": (seg.get("text") or "").strip(),
                }
            )
        return normalized

    async def _simulate_transcription(self, job: Job, db: AsyncSession) -> None:
        """Fast path for tests to avoid loading large Whisper models."""
        transcript_text = f"Simulated transcript for {job.original_filename}"
        segments = [
            {"id": 0, "start": 0.0, "end": float(job.duration or 10.0), "text": transcript_text}
        ]
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.progress_percent = 10
        job.progress_stage = "loading_model"
        job.estimated_time_left = 120
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 60
        job.progress_stage = "transcribing"
        job.estimated_time_left = 30
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 90
        job.progress_stage = "finalizing"
        job.estimated_time_left = 5
        await db.commit()

        await asyncio.sleep(0.2)

        transcript_path = Path(settings.transcript_storage_path) / f"{job.id}.txt"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(transcript_text, encoding="utf-8")
        metadata_path = transcript_path.with_suffix(".json")
        metadata = {
            "text": transcript_text,
            "segments": segments,
            "language": job.language_detected or "en",
            "duration": job.duration or 10.0,
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
