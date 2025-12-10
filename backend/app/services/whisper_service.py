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
from app.models.user_settings import UserSettings
from app.models.transcript import Transcript
from app.models.system_preferences import SystemPreferences
from app.services.capabilities import enforce_runtime_diarizer, get_asr_candidate_order
from app.services.provider_manager import ProviderManager

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

    async def _load_model_from_record(self, record) -> Any:
        """Load a Whisper model using a registry record's abs_path."""

        async with _model_lock:
            cache_key = f"{record.set_name}:{record.name}"
            if cache_key in _model_cache:
                logger.info(
                    "Using cached Whisper model: %s (set=%s path=%s)",
                    cache_key,
                    record.set_name,
                    record.abs_path,
                )
                return _model_cache[cache_key]

            try:
                import whisper
            except ImportError:
                raise ImportError(
                    "openai-whisper package not installed. Install with: pip install openai-whisper"
                )

            model_path = Path(record.abs_path)
            if model_path.is_file():
                download_root = model_path.parent
                model_name = model_path.stem
            elif model_path.is_dir():
                candidate = model_path / f"{record.name}.pt"
                if candidate.exists():
                    download_root = model_path
                    model_name = record.name
                else:
                    pt_files = list(model_path.glob("*.pt"))
                    if not pt_files:
                        raise FileNotFoundError(
                            f"No .pt file found in {model_path}; cannot load Whisper model {record.name}"
                        )
                    download_root = model_path
                    model_name = pt_files[0].stem
            else:
                raise FileNotFoundError(f"Model path does not exist: {model_path}")

            logger.info(
                "Loading Whisper model from registry set=%s entry=%s path=%s (resolved name=%s, root=%s)",
                record.set_name,
                record.name,
                model_path,
                model_name,
                download_root,
            )
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None, lambda: whisper.load_model(model_name, download_root=str(download_root))
            )

            _model_cache[cache_key] = model
            logger.info("Successfully loaded Whisper model %s from %s", model_name, download_root)
            return model

    async def transcribe_audio(
        self,
        audio_path: str,
        model_name: str,
        language: Optional[str] = None,
        enable_timestamps: bool = True,
        enable_speaker_detection: bool = False,
        *,
        model_obj: Any = None,
    ) -> Dict[str, Any]:
        """Transcribe an audio/video file using Whisper.

        Args:
            audio_path: Path to audio/video file
            model_name: Whisper model to use
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            enable_timestamps: Include word-level timestamps
            enable_speaker_detection: Enable speaker diarization (requires pyannote)
            model_obj: Optional pre-loaded whisper model (bypasses internal load)

        Returns:
            Dictionary with transcription results.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting transcription: {audio_path} with model {model_name}")

        try:
            model = model_obj or await self.load_model(model_name)

            transcribe_options = {
                "language": language if language and language != "auto" else None,
                "task": "transcribe",
                "verbose": False,
            }

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: model.transcribe(audio_path, **transcribe_options)
            )

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

            logger.info(
                f"Transcription complete: {len(transcript_result['segments'])} segments, "
                f"{transcript_result['duration']:.1f}s duration"
            )

            return transcript_result

        except Exception as exc:
            logger.error(f"Transcription failed for {audio_path}: {exc}")
            raise RuntimeError(f"Transcription failed: {str(exc)}") from exc

    def _probe_duration_seconds(self, audio_path: Path) -> Optional[float]:
        """Best-effort duration probe using ffmpeg, returning None on failure."""
        try:
            import ffmpeg
        except ImportError:
            return None

        try:
            probe = ffmpeg.probe(str(audio_path))
            fmt = probe.get("format") or {}
            dur = fmt.get("duration")
            if dur is not None:
                return float(dur)
        except Exception as exc:  # best effort
            logger.warning("Could not probe duration for %s: %s", audio_path, exc)
        return None

    def _resolve_diarizer_record(self, name: Optional[str]):
        if not name:
            return None
        snapshot = ProviderManager.get_snapshot()
        return next((r for r in snapshot["diarizers"] if r.name == name and r.enabled), None)

    async def _get_system_preferences(self, db: AsyncSession) -> SystemPreferences:
        result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
        prefs = result.scalar_one_or_none()
        if not prefs:
            prefs = SystemPreferences(id=1, server_time_zone="UTC", transcode_to_wav=True)
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)
        return prefs

    def _transcode_to_wav(self, src: Path, job_id: str) -> Path:
        """Transcode a source audio/video file to WAV for downstream processing."""
        try:
            import ffmpeg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("ffmpeg-python not installed") from exc

        dst = Path(settings.media_storage_path) / f"{src.stem}-{job_id}-pcm.wav"
        dst.parent.mkdir(parents=True, exist_ok=True)
        stream = ffmpeg.input(str(src))
        out = ffmpeg.output(stream, str(dst), format="wav", acodec="pcm_s16le")
        ffmpeg.run(out, overwrite_output=True, quiet=True)
        return dst

    def _diarizer_available(self, record) -> bool:
        if not record:
            return False
        model_path = Path(record.abs_path)
        if not model_path.exists():
            logger.warning("Diarizer path missing for %s: %s", record.name, model_path)
            return False
        config_path = model_path / "config.yaml" if model_path.is_dir() else model_path
        if not config_path.exists():
            logger.warning("Diarizer config missing for %s at %s", record.name, config_path)
            return False
        try:
            import torchaudio  # type: ignore

            if not hasattr(torchaudio, "set_audio_backend"):
                torchaudio.set_audio_backend = lambda *args, **kwargs: None  # type: ignore[attr-defined]
            if not hasattr(torchaudio, "get_audio_backend"):
                torchaudio.get_audio_backend = lambda *args, **kwargs: None  # type: ignore[attr-defined]
            if not hasattr(torchaudio, "list_audio_backends"):
                torchaudio.list_audio_backends = lambda *args, **kwargs: []  # type: ignore[attr-defined]
            else:
                try:
                    torchaudio.set_audio_backend("soundfile")  # type: ignore[attr-defined]
                except Exception:
                    torchaudio.set_audio_backend = lambda *args, **kwargs: None  # fallback no-op
        except ImportError:
            pass
        try:
            import torch  # noqa: F401
            import pyannote.audio  # noqa: F401
        except ImportError as exc:
            logger.warning("Diarizer '%s' not available (missing deps): %s", record.name, exc)
            return False
        except Exception as exc:
            logger.warning("Diarizer '%s' import error: %s", record.name, exc)
            return False
        return True

    async def _run_diarization(self, audio_path: str, record) -> Dict[str, Any]:
        """Run pyannote diarization for a given registry record."""
        try:
            import torchaudio  # type: ignore

            if not hasattr(torchaudio, "set_audio_backend"):
                torchaudio.set_audio_backend = lambda *args, **kwargs: None  # type: ignore[attr-defined]
            if not hasattr(torchaudio, "get_audio_backend"):
                torchaudio.get_audio_backend = lambda *args, **kwargs: None  # type: ignore[attr-defined]
            if not hasattr(torchaudio, "list_audio_backends"):
                torchaudio.list_audio_backends = lambda *args, **kwargs: []  # type: ignore[attr-defined]
            else:
                try:
                    torchaudio.set_audio_backend("soundfile")  # type: ignore[attr-defined]
                except Exception:
                    torchaudio.set_audio_backend = lambda *args, **kwargs: None  # fallback no-op
            from pyannote.audio import Pipeline
        except ImportError as exc:
            raise RuntimeError(f"pyannote.audio not installed: {exc}") from exc

        model_path = Path(record.abs_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Diarizer path not found: {model_path}")

        # Allow admin to point to either a directory containing config.yaml or the config file itself.
        if model_path.is_dir():
            config_path = model_path / "config.yaml"
            base_dir = model_path
        else:
            config_path = model_path
            base_dir = model_path.parent

        if not config_path.exists():
            raise FileNotFoundError(f"Diarizer config not found at {config_path}")

        # Ensure torch is imported in this scope so any nested helpers and finally blocks
        # can reference it without tripping a NameError if pyannote throws mid-load.
        try:
            import numpy as np  # type: ignore

            # Numpy 2.x dropped the legacy NAN alias; pyannote still references it.
            if not hasattr(np, "NAN"):
                np.NAN = np.nan  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Unable to import torch before initializing diarizer pipeline")
            raise

        # Rewrite HF repo references in config.yaml to local checkpoint files if present
        # so Pipeline/Model.from_pretrained skip hub validation and stay offline.
        def _rewrite_local_paths(obj):
            if isinstance(obj, dict):
                return {k: _rewrite_local_paths(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_rewrite_local_paths(v) for v in obj]
            if isinstance(obj, str):
                # Look for a local directory matching the repo id tail and pick a .bin inside it.
                tail = obj.split("/")[-1]
                candidate_dir = base_dir / tail
                candidate_file = candidate_dir / "pytorch_model.bin"
                if candidate_file.exists():
                    logger.info("Using local diarizer checkpoint for %s -> %s", obj, candidate_file)
                    return str(candidate_file)
                # fallback: any .bin inside the candidate dir
                if candidate_dir.is_dir():
                    bin_files = list(candidate_dir.glob("*.bin"))
                    if bin_files:
                        chosen = bin_files[0]
                        logger.info("Using local diarizer checkpoint for %s -> %s", obj, chosen)
                        return str(chosen)
            return obj

        import yaml

        with config_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        rewritten = _rewrite_local_paths(config_data)
        local_config_path = base_dir / "_local_config.generated.yaml"
        with local_config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(rewritten, f)

        temp_wav: Optional[Path] = None

        def _load_waveform(path: Path):
            nonlocal temp_wav
            try:
                import torchaudio  # type: ignore

                waveform, sample_rate = torchaudio.load(str(path))
                return waveform, sample_rate
            except Exception as exc:
                logger.warning(
                    "Primary audio load for diarization failed (%s); attempting ffmpeg re-encode",
                    exc,
                )
                # Fallback 1: soundfile (if available) without re-encode
                try:
                    import soundfile as sf  # type: ignore
                    import torch

                    data, sample_rate = sf.read(str(path))
                    tensor = torch.tensor(data, dtype=torch.float32)
                    if tensor.ndim == 1:
                        tensor = tensor.unsqueeze(0)
                    else:
                        tensor = tensor.transpose(0, 1)
                    return tensor, sample_rate
                except Exception as sf_exc:
                    logger.warning(
                        "soundfile load also failed (%s); attempting ffmpeg re-encode", sf_exc
                    )
                try:
                    import ffmpeg  # type: ignore
                except ImportError:
                    raise RuntimeError(
                        "torchaudio/soundfile could not read diarization input and ffmpeg is missing"
                    ) from exc
                temp_wav = base_dir / f"{path.stem}-diarizer-reencode.wav"
                stream = ffmpeg.input(str(path))
                out = ffmpeg.output(
                    stream, str(temp_wav), format="wav", acodec="pcm_s16le", ar=16000, ac=1
                )
                ffmpeg.run(out, overwrite_output=True, quiet=True)
                try:
                    import soundfile as sf  # type: ignore
                    import torch

                    data, sample_rate = sf.read(str(temp_wav))
                    tensor = torch.tensor(data, dtype=torch.float32)
                    if tensor.ndim == 1:
                        tensor = tensor.unsqueeze(0)
                    else:
                        tensor = tensor.transpose(0, 1)
                    return tensor, sample_rate
                except Exception as final_exc:
                    logger.warning("Even re-encoded diarizer audio load failed (%s)", final_exc)
                    raise

        def _infer():
            import torch
            import torch.serialization as ser

            original_load = torch.load
            original_ser_load = ser.load

            def _load_weights_friendly(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return original_load(*args, **kwargs)

            def _ser_load_weights_friendly(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return original_ser_load(*args, **kwargs)

            torch.load = _load_weights_friendly  # type: ignore[assignment]
            ser.load = _ser_load_weights_friendly  # type: ignore[assignment]
            if hasattr(ser, "_set_default_weights_only"):
                try:
                    ser._set_default_weights_only(False)  # type: ignore[attr-defined]
                except Exception:
                    pass
            try:
                pipeline = Pipeline.from_pretrained(str(local_config_path))
                try:
                    waveform, sample_rate = _load_waveform(Path(audio_path))
                    diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})
                except Exception as exc:
                    logger.warning(
                        "Falling back to path-based diarization load after waveform decode failure: %s",
                        exc,
                    )
                    diarization = pipeline(audio_path)
                speakers = set()
                for segment, _, label in diarization.itertracks(yield_label=True):
                    speakers.add(label)
                return {"speaker_count": max(1, len(speakers)), "raw": diarization}
            finally:
                torch.load = original_load  # type: ignore[assignment]
                ser.load = original_ser_load  # type: ignore[assignment]
                if temp_wav:
                    with suppress(Exception):
                        temp_wav.unlink(missing_ok=True)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _infer)

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

        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == job.user_id)
        )
        user_settings = settings_result.scalar_one_or_none()
        system_preferences = await self._get_system_preferences(db)

        progress_task: Optional[asyncio.Task] = None
        fast_path = settings.is_testing or settings.e2e_fast_transcription
        transcoded_path: Optional[Path] = None
        audio_path_for_processing: str = job.file_path
        try:
            if fast_path:
                await self._wait_for_processing_slot(db)
            if fast_path:
                await self._simulate_transcription(job, db)
                logger.info(f"Job {job_id} completed via simulated transcription")
                return
            # Check if already cancelled
            if self._is_cancelled_state(job):
                await self._finalize_cancellation(job, db, "before processing")
                return

            runtime_diarizer = enforce_runtime_diarizer(
                requested_diarizer=job.diarizer_used,
                diarization_requested=bool(job.has_speaker_labels),
                user_settings=user_settings,
            )
            if runtime_diarizer["notes"]:
                for note in runtime_diarizer["notes"]:
                    logger.warning("Job %s diarization adjustment: %s", job_id, note)
            job.has_speaker_labels = runtime_diarizer["diarization_enabled"]
            job.diarizer_used = runtime_diarizer["diarizer"]
            if not job.has_speaker_labels:
                job.speaker_count = None
            diarizer_record = self._resolve_diarizer_record(job.diarizer_used)
            diarizer_ready = (
                self._diarizer_available(diarizer_record) if job.has_speaker_labels else False
            )
            if not diarizer_ready:
                if job.diarizer_used:
                    logger.warning(
                        "Job %s diarizer %s not runnable on this system; proceeding without diarization",
                        job_id,
                        job.diarizer_used,
                    )
                    job.diarizer_used = f"{job.diarizer_used} (failed)"
                job.has_speaker_labels = False
                job.speaker_count = 1

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

            if await self._abort_if_cancelled(job, db, "before resolving model availability"):
                return

            # Resolve model candidates from registry (provider + entry)
            preferred_provider = user_settings.default_asr_provider if user_settings else None
            snapshot = ProviderManager.get_snapshot()
            enabled_asr = snapshot["asr"]
            candidate_models = get_asr_candidate_order(job.model_used, user_settings)

            def pick_records(names: list[str], preferred: Optional[str]):
                records = []
                for name in names:
                    pref = next(
                        (
                            r
                            for r in enabled_asr
                            if r.name == name and (preferred is None or r.set_name == preferred)
                        ),
                        None,
                    )
                    if pref:
                        records.append(pref)
                        continue
                    fallback = next((r for r in enabled_asr if r.name == name), None)
                    if fallback:
                        records.append(fallback)
                return records

            candidate_records = pick_records(candidate_models, preferred_provider)
            if not candidate_records:
                raise RuntimeError("No Whisper models are available in the registry.")

            resolved_record = None
            last_error: Optional[Exception] = None
            for record in candidate_records:
                try:
                    await self._load_model_from_record(record)
                    resolved_record = record
                    break
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Job %s model '%s/%s' unavailable; trying next candidate (%s)",
                        job_id,
                        record.set_name,
                        record.name,
                        exc,
                    )
            if resolved_record is None:
                raise RuntimeError(
                    "No Whisper models are available in the configured model directory."
                ) from last_error

            logger.info(
                "Job %s using ASR model set=%s entry=%s abs_path=%s",
                job_id,
                resolved_record.set_name,
                resolved_record.name,
                resolved_record.abs_path,
            )
            if resolved_record.name != job.model_used:
                logger.warning(
                    "Job %s model fallback applied: %s -> %s",
                    job_id,
                    job.model_used,
                    resolved_record.name,
                )
                job.model_used = resolved_record.name
                await db.commit()
                await db.refresh(job)

            model_name = resolved_record.name
            language = job.language_detected if job.language_detected != "auto" else None

            # Optional transcode to WAV for better backend compatibility (pyannote on CPU).
            if (
                system_preferences.transcode_to_wav
                and Path(audio_path_for_processing).suffix.lower() != ".wav"
            ):
                try:
                    transcoded_path = self._transcode_to_wav(Path(job.file_path), job.id)
                    audio_path_for_processing = str(transcoded_path)
                    logger.info("Job %s transcoded input to WAV at %s", job_id, transcoded_path)
                except Exception as exc:
                    logger.warning(
                        "Job %s failed to transcode input to WAV: %s; continuing with original file",
                        job_id,
                        exc,
                    )

            if await self._abort_if_cancelled(job, db, "after selecting model"):
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

            # Perform transcription using the resolved record/path
            model_obj = await self._load_model_from_record(resolved_record)
            transcript_result = await self.transcribe_audio(
                audio_path=audio_path_for_processing,
                model_name=model_name,
                language=language,
                enable_timestamps=job.has_timestamps,
                enable_speaker_detection=job.has_speaker_labels,
                model_obj=model_obj,
            )

            if job.has_speaker_labels and diarizer_ready and diarizer_record:
                try:
                    diarization_result = await self._run_diarization(
                        audio_path_for_processing, diarizer_record
                    )
                    job.speaker_count = diarization_result.get("speaker_count") or 1
                    logger.info(
                        "Job %s diarization success using %s: %s speakers",
                        job_id,
                        diarizer_record.name,
                        job.speaker_count,
                    )
                except Exception as exc:
                    logger.warning(
                        "Job %s diarization failed with %s: %s; falling back to 1 speaker",
                        job_id,
                        diarizer_record.name,
                        exc,
                    )
                    job.diarizer_used = f"{job.diarizer_used} (failed)"
                    job.has_speaker_labels = False
                    job.speaker_count = 1

            duration = transcript_result.get("duration") or 0.0
            if duration <= 0 and job.duration:
                duration = job.duration
            if duration <= 0:
                probed = self._probe_duration_seconds(Path(audio_path_for_processing))
                if probed:
                    duration = probed
            if duration <= 0:
                duration = float(settings.default_estimated_duration_seconds)
            transcript_result["duration"] = float(duration)

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
            if not job.speaker_count:
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
        finally:
            if transcoded_path:
                with suppress(Exception):
                    transcoded_path.unlink(missing_ok=True)

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
        factor = self._model_speed_factor(job.model_used or "unknown")
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
