"""Whisper model management and transcription service.

Handles loading Whisper models, processing audio/video files,
and generating transcriptions with timestamps and speaker labels.
"""

import asyncio
from contextlib import suppress
from datetime import datetime
import json
import math
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
from app.services.settings_resolver import build_effective_user_settings, get_admin_settings

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading
_model_cache: Dict[str, Any] = {}
_model_lock = asyncio.Lock()
CHECKPOINT_VERSION = 1
DEFAULT_CHUNK_SECONDS = 10


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

    def _is_pause_state(self, job: Job) -> bool:
        return job.status in {"paused", "pausing"}

    async def _finalize_cancellation(self, job: Job, db: AsyncSession, context: str) -> None:
        """Finalize a cancellation by ensuring consistent state and logging."""
        if job.started_at:
            job.processing_seconds = int(job.processing_seconds or 0) + int(
                (datetime.utcnow() - job.started_at).total_seconds()
            )
        job.status = "cancelled"
        job.progress_stage = None
        job.estimated_time_left = None
        if job.completed_at is None:
            job.completed_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Job {job.id} cancellation acknowledged ({context})")

    async def _finalize_pause(self, job: Job, db: AsyncSession, context: str) -> None:
        """Finalize a pause by ensuring consistent state and logging."""
        if job.started_at:
            job.processing_seconds = int(job.processing_seconds or 0) + int(
                (datetime.utcnow() - job.started_at).total_seconds()
            )
        job.status = "paused"
        job.paused_at = job.paused_at or datetime.utcnow()
        job.progress_stage = "paused"
        job.estimated_time_left = None
        await db.commit()
        logger.info("Job %s pause acknowledged (%s)", job.id, context)

    async def _abort_if_cancelled(self, job: Job, db: AsyncSession, context: str) -> bool:
        await db.refresh(job)
        if self._is_cancelled_state(job):
            await self._finalize_cancellation(job, db, context)
            return True
        return False

    async def _abort_if_pausing(self, job: Job, db: AsyncSession, context: str) -> bool:
        await db.refresh(job)
        if job.status == "pausing":
            await self._finalize_pause(job, db, context)
            return True
        if job.status == "paused":
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
            prefs = SystemPreferences(
                id=1,
                server_time_zone="UTC",
                transcode_to_wav=True,
                enable_empty_weights=False,
            )
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

    def _checkpoint_root(self, job_id: str) -> Path:
        return Path(settings.transcript_storage_path) / job_id

    def _checkpoint_path(self, job_id: str) -> Path:
        return self._checkpoint_root(job_id) / "checkpoint.json"

    def _chunk_dir(self, job_id: str) -> Path:
        return self._checkpoint_root(job_id) / "chunks"

    def _load_checkpoint(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception as exc:
            logger.warning("Failed to read checkpoint %s: %s", path, exc)
        return None

    def _write_checkpoint(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _build_checkpoint(
        self,
        job: Job,
        *,
        audio_path: str,
        model_name: str,
        language: Optional[str],
        chunk_seconds: int,
        total_duration: float,
    ) -> Dict[str, Any]:
        return {
            "version": CHECKPOINT_VERSION,
            "job_id": job.id,
            "audio_path": audio_path,
            "model_name": model_name,
            "language": language,
            "chunk_seconds": chunk_seconds,
            "total_duration": total_duration,
            "next_index": 0,
            "segments": [],
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _render_chunk(
        self, audio_path: str, chunk_path: Path, *, start: float, duration: float
    ) -> None:
        try:
            import ffmpeg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("ffmpeg-python not installed") from exc

        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        stream = ffmpeg.input(str(audio_path), ss=start, t=duration)
        out = ffmpeg.output(stream, str(chunk_path), format="wav", acodec="pcm_s16le")
        ffmpeg.run(out, overwrite_output=True, quiet=True)

    def _diarizer_available(self, record) -> bool:
        if not record:
            return False
        provider = (record.set_name or "").lower()
        model_path = Path(record.abs_path)
        if not model_path.exists():
            logger.warning("Diarizer path missing for %s: %s", record.name, model_path)
            return False

        if provider in {"pyannote", "whisperx"}:
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
                        torchaudio.set_audio_backend = (
                            lambda *args, **kwargs: None
                        )  # fallback no-op
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

        if provider == "vad":
            return True

        logger.warning("Diarizer provider '%s' is not supported yet", provider)
        return False

    def _collect_diarization_segments(self, diarization: Any) -> list[Dict[str, Any]]:
        """Extract diarization segments from a pyannote Annotation."""
        segments: list[Dict[str, Any]] = []
        if diarization is None:
            return segments
        try:
            iterator = diarization.itertracks(yield_label=True)
        except Exception:
            return segments
        for segment, _, label in iterator:
            start = float(getattr(segment, "start", 0.0) or 0.0)
            end = float(getattr(segment, "end", 0.0) or 0.0)
            if end <= start:
                continue
            segments.append({"start": start, "end": end, "speaker": str(label)})
        return segments

    def _assign_speaker_labels(
        self, segments: list[Dict[str, Any]], diarization_segments: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """Assign speaker labels to transcript segments by time overlap."""
        if not diarization_segments:
            return segments
        for segment in segments:
            seg_start = float(segment.get("start") or 0.0)
            seg_end = float(segment.get("end") or 0.0)
            if seg_end <= seg_start:
                continue
            best_speaker = None
            best_overlap = 0.0
            for diar in diarization_segments:
                diar_start = float(diar.get("start") or 0.0)
                diar_end = float(diar.get("end") or 0.0)
                overlap = min(seg_end, diar_end) - max(seg_start, diar_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar.get("speaker")
            if best_speaker:
                segment["speaker"] = best_speaker
        return segments

    def _apply_single_speaker_label(self, segments: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Apply a single speaker label across all transcript segments."""
        for segment in segments:
            segment["speaker"] = segment.get("speaker") or "Speaker 1"
        return segments

    async def _run_pyannote_diarization(
        self, audio_path: str, record, *, speaker_count_hint: Optional[int] = None
    ) -> Dict[str, Any]:
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
                diarization_args: Dict[str, Any] = {}
                if speaker_count_hint is not None and speaker_count_hint >= 2:
                    diarization_args["num_speakers"] = speaker_count_hint
                try:
                    waveform, sample_rate = _load_waveform(Path(audio_path))
                    diarization = pipeline(
                        {"waveform": waveform, "sample_rate": sample_rate}, **diarization_args
                    )
                except Exception as exc:
                    logger.warning(
                        "Falling back to path-based diarization load after waveform decode failure: %s",
                        exc,
                    )
                    diarization = pipeline(audio_path, **diarization_args)
                diarization_segments = self._collect_diarization_segments(diarization)
                speakers = {seg["speaker"] for seg in diarization_segments if seg.get("speaker")}
                return {
                    "speaker_count": max(1, len(speakers)),
                    "raw": diarization,
                    "segments": diarization_segments,
                }
            finally:
                torch.load = original_load  # type: ignore[assignment]
                ser.load = original_ser_load  # type: ignore[assignment]
                if temp_wav:
                    with suppress(Exception):
                        temp_wav.unlink(missing_ok=True)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _infer)

    async def _run_vad_diarization(self, audio_path: str, record) -> Dict[str, Any]:
        """Fallback diarization that tags a single speaker when VAD is selected."""
        return {"speaker_count": 1, "segments": [], "raw": None}

    async def _run_diarization(
        self, audio_path: str, record, *, speaker_count_hint: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run diarization for the given registry record."""
        provider = (record.set_name or "").lower() if record else ""
        if provider in {"pyannote", "whisperx"}:
            if provider == "whisperx":
                logger.info("Using pyannote pipeline for whisperx diarizer provider")
            return await self._run_pyannote_diarization(
                audio_path, record, speaker_count_hint=speaker_count_hint
            )
        if provider == "vad":
            return await self._run_vad_diarization(audio_path, record)
        raise RuntimeError(f"Unsupported diarizer provider: {provider or 'unknown'}")

    async def _transcribe_with_checkpoints(
        self,
        job: Job,
        db: AsyncSession,
        *,
        audio_path: str,
        model_name: str,
        language: Optional[str],
        enable_timestamps: bool,
        model_obj: Any,
    ) -> Optional[Dict[str, Any]]:
        checkpoint_path = self._checkpoint_path(job.id)
        checkpoint = self._load_checkpoint(checkpoint_path)

        total_duration = None
        if checkpoint:
            total_duration = checkpoint.get("total_duration")
        if not total_duration:
            total_duration = self._probe_duration_seconds(Path(audio_path)) or job.duration
        if not total_duration:
            total_duration = float(settings.default_estimated_duration_seconds)

        chunk_seconds = (
            int(checkpoint.get("chunk_seconds", DEFAULT_CHUNK_SECONDS))
            if checkpoint
            else DEFAULT_CHUNK_SECONDS
        )
        if not checkpoint:
            checkpoint = self._build_checkpoint(
                job,
                audio_path=audio_path,
                model_name=model_name,
                language=language,
                chunk_seconds=chunk_seconds,
                total_duration=float(total_duration),
            )
        checkpoint.setdefault("segments", [])
        checkpoint.setdefault("next_index", 0)
        checkpoint["audio_path"] = audio_path
        checkpoint["model_name"] = model_name
        if language:
            checkpoint["language"] = language

        job.checkpoint_path = str(checkpoint_path)
        await db.commit()

        total_chunks = max(1, int(math.ceil(float(total_duration) / chunk_seconds)))
        next_index = int(checkpoint.get("next_index") or 0)
        segments: list[Dict[str, Any]] = checkpoint["segments"]
        if next_index >= total_chunks:
            logger.info(
                "Job %s checkpoint already complete (chunk %s of %s); proceeding to finalization",
                job.id,
                next_index,
                total_chunks,
            )
        elif next_index > 0:
            logger.info(
                "Job %s resuming transcription from checkpoint chunk %s of %s",
                job.id,
                next_index,
                total_chunks,
            )
        else:
            logger.info("Job %s starting transcription from chunk 0 of %s", job.id, total_chunks)

        for index in range(next_index, total_chunks):
            if await self._abort_if_cancelled(job, db, f"checkpoint chunk {index}"):
                return None
            if await self._abort_if_pausing(job, db, f"checkpoint chunk {index}"):
                checkpoint["updated_at"] = datetime.utcnow().isoformat()
                self._write_checkpoint(checkpoint_path, checkpoint)
                return None

            start = index * chunk_seconds
            duration = max(0.0, min(chunk_seconds, float(total_duration) - start))
            chunk_path = self._chunk_dir(job.id) / f"chunk-{index:04d}.wav"
            if not chunk_path.exists():
                try:
                    self._render_chunk(audio_path, chunk_path, start=start, duration=duration)
                except Exception as exc:
                    logger.warning(
                        "Chunk render failed for job %s (index %s): %s. Falling back to full-file transcription.",
                        job.id,
                        index,
                        exc,
                    )
                    transcript_result = await self.transcribe_audio(
                        audio_path=audio_path,
                        model_name=model_name,
                        language=language,
                        enable_timestamps=enable_timestamps,
                        enable_speaker_detection=False,
                        model_obj=model_obj,
                    )
                    if checkpoint_path.exists():
                        with suppress(Exception):
                            checkpoint_path.unlink()
                    job.checkpoint_path = None
                    await db.commit()
                    return transcript_result

            chunk_result = await self.transcribe_audio(
                audio_path=str(chunk_path),
                model_name=model_name,
                language=language,
                enable_timestamps=enable_timestamps,
                enable_speaker_detection=False,
                model_obj=model_obj,
            )

            offset = start
            for seg in chunk_result.get("segments", []):
                segments.append(
                    {
                        "id": seg.get("id"),
                        "start": float(seg.get("start", 0.0)) + offset,
                        "end": float(seg.get("end", 0.0)) + offset,
                        "text": seg.get("text", ""),
                        "speaker": seg.get("speaker"),
                    }
                )

            if not checkpoint.get("language"):
                checkpoint["language"] = chunk_result.get("language")

            checkpoint["segments"] = segments
            checkpoint["next_index"] = index + 1
            checkpoint["updated_at"] = datetime.utcnow().isoformat()
            self._write_checkpoint(checkpoint_path, checkpoint)

            asr_seconds, _, total_seconds = self._estimate_stage_seconds(
                job, duration_hint=total_duration
            )
            asr_weight = asr_seconds / total_seconds if total_seconds else 1.0
            progress_ratio = (index + 1) / total_chunks
            estimated_progress = int(progress_ratio * asr_weight * 100)
            job.progress_percent = max(int(job.progress_percent or 0), estimated_progress)
            job.progress_stage = "transcribing"
            job.estimated_time_left = max(int((total_chunks - index - 1) * chunk_seconds), 0)
            job.updated_at = datetime.utcnow()
            await db.commit()

        normalized_segments = self._normalize_segments(segments)
        formatted_text = self._format_full_text(
            normalized_segments,
            include_timestamps=enable_timestamps,
            include_speakers=False,
        )
        transcript_result = {
            "text": formatted_text,
            "segments": normalized_segments,
            "language": checkpoint.get("language") or "unknown",
            "duration": float(total_duration),
        }
        return transcript_result

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
        if self._is_pause_state(job):
            if job.status == "pausing":
                await self._finalize_pause(job, db, "job fetched")
            return

        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == job.user_id)
        )
        user_settings = settings_result.scalar_one_or_none()
        admin_settings = await get_admin_settings(db) if user_settings else None
        effective_settings = build_effective_user_settings(user_settings, admin_settings)
        system_preferences = await self._get_system_preferences(db)

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
            if self._is_pause_state(job):
                if job.status == "pausing":
                    await self._finalize_pause(job, db, "before processing")
                return

            runtime_diarizer = enforce_runtime_diarizer(
                requested_diarizer=job.diarizer_used,
                diarization_requested=bool(job.has_speaker_labels),
                user_settings=effective_settings,
            )
            if runtime_diarizer["notes"]:
                for note in runtime_diarizer["notes"]:
                    logger.warning("Job %s diarization adjustment: %s", job_id, note)
            job.has_speaker_labels = runtime_diarizer["diarization_enabled"]
            job.diarizer_used = runtime_diarizer["diarizer"]
            if not job.has_speaker_labels:
                job.speaker_count = None
            diarizer_record = self._resolve_diarizer_record(job.diarizer_used)
            job.diarizer_provider_used = diarizer_record.set_name if diarizer_record else None
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
            job.progress_percent = 0
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
            if await self._abort_if_pausing(job, db, "before resolving model availability"):
                return

            # Resolve model candidates from registry (provider + entry)
            preferred_provider = (
                effective_settings.default_asr_provider if effective_settings else None
            )
            snapshot = ProviderManager.get_snapshot()
            enabled_asr = snapshot["asr"]
            candidate_models = get_asr_candidate_order(job.model_used, effective_settings)

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
            job.asr_provider_used = resolved_record.set_name
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
            if await self._abort_if_pausing(job, db, "after selecting model"):
                return

            # Stage 2: Transcribing
            job.progress_percent = 0
            job.progress_stage = "transcribing"
            job.estimated_time_left = job.estimated_time_left or job.estimated_total_seconds
            await db.commit()

            if await self._abort_if_cancelled(job, db, "before transcription"):
                return
            if await self._abort_if_pausing(job, db, "before transcription"):
                return

            # Perform transcription using the resolved record/path
            model_obj = await self._load_model_from_record(resolved_record)
            transcript_result = await self._transcribe_with_checkpoints(
                job,
                db,
                audio_path=audio_path_for_processing,
                model_name=model_name,
                language=language,
                enable_timestamps=job.has_timestamps,
                model_obj=model_obj,
            )
            if transcript_result is None:
                return

            diarization_attempted = False
            if job.has_speaker_labels and diarizer_ready and diarizer_record:
                try:
                    asr_seconds, diar_seconds, total_seconds = self._estimate_stage_seconds(
                        job, duration_hint=job.duration
                    )
                    asr_weight = asr_seconds / total_seconds if total_seconds else 1.0
                    job.progress_stage = "diarizing"
                    diar_floor = int(asr_weight * 100)
                    job.progress_percent = max(int(job.progress_percent or 0), diar_floor)
                    await db.commit()
                    diar_task = asyncio.create_task(
                        self._drain_progress_during_diarization(
                            job_id,
                            start_percent=diar_floor,
                            end_percent=95,
                            expected_seconds=diar_seconds or 1.0,
                        )
                    )
                    speaker_count_hint = (
                        job.speaker_count if job.speaker_count and job.speaker_count > 1 else None
                    )
                    try:
                        diarization_result = await self._run_diarization(
                            audio_path_for_processing,
                            diarizer_record,
                            speaker_count_hint=speaker_count_hint,
                        )
                    finally:
                        diar_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await diar_task
                    job.speaker_count = diarization_result.get("speaker_count") or 1
                    diarization_segments = diarization_result.get("segments") or []
                    if diarization_segments:
                        transcript_result["segments"] = self._assign_speaker_labels(
                            transcript_result["segments"], diarization_segments
                        )
                        transcript_result["text"] = self._format_full_text(
                            transcript_result["segments"],
                            include_timestamps=job.has_timestamps,
                            include_speakers=True,
                        )
                    elif diarizer_record.set_name.lower() == "vad":
                        transcript_result["segments"] = self._apply_single_speaker_label(
                            transcript_result["segments"]
                        )
                        transcript_result["text"] = self._format_full_text(
                            transcript_result["segments"],
                            include_timestamps=job.has_timestamps,
                            include_speakers=True,
                        )
                    logger.info(
                        "Job %s diarization success using %s: %s speakers",
                        job_id,
                        diarizer_record.name,
                        job.speaker_count,
                    )
                    diar_completion = int(((asr_seconds + diar_seconds) / total_seconds) * 100)
                    diar_completion = min(max(diar_completion, diar_floor), 95)
                    job.progress_percent = max(int(job.progress_percent or 0), diar_completion)
                    diarization_attempted = True
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
                    diarization_attempted = True

            if diarization_attempted:
                await db.commit()

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
                return
            if await self._abort_if_pausing(job, db, "after transcription"):
                return

            # Stage 3: Finalizing
            job.progress_percent = max(int(job.progress_percent or 0), 95)
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
            if job.started_at:
                job.processing_seconds = int(job.processing_seconds or 0) + int(
                    (datetime.utcnow() - job.started_at).total_seconds()
                )
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

            if job.checkpoint_path:
                checkpoint_path = Path(job.checkpoint_path)
                if checkpoint_path.exists():
                    with suppress(Exception):
                        checkpoint_path.unlink()
                with suppress(Exception):
                    chunk_dir = checkpoint_path.parent / "chunks"
                    if chunk_dir.exists():
                        for item in chunk_dir.glob("*.wav"):
                            item.unlink(missing_ok=True)
                        chunk_dir.rmdir()
                job.checkpoint_path = None
                await db.commit()

        except Exception as exc:
            await db.refresh(job)
            if self._is_cancelled_state(job):
                await self._finalize_cancellation(job, db, "during exception")
                return
            if self._is_pause_state(job):
                await self._finalize_pause(job, db, "during exception")
                return
            if job.started_at:
                job.processing_seconds = int(job.processing_seconds or 0) + int(
                    (datetime.utcnow() - job.started_at).total_seconds()
                )
                job.started_at = None
            logger.error(f"Job {job_id} failed: {exc}")
            job.status = "failed"
            job.progress_stage = None
            job.estimated_time_left = None
            job.error_message = str(exc)
            await db.commit()
        finally:
            if transcoded_path:
                await db.refresh(job)
                if job.status not in {"paused", "pausing"}:
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

    def _diarization_speed_factor(self, job: Job) -> float:
        """Approximate realtime factor for diarization."""
        provider = (job.diarizer_provider_used or "").lower()
        if provider == "vad":
            return 0.1
        return 0.75

    def _estimate_stage_seconds(
        self, job: Job, duration_hint: Optional[float] = None
    ) -> tuple[float, float, float]:
        """Estimate ASR/diarization seconds and total."""
        duration = duration_hint if duration_hint is not None else job.duration
        base_seconds = float(duration or settings.default_estimated_duration_seconds)
        asr_seconds = max(base_seconds * self._model_speed_factor(job.model_used or "unknown"), 1.0)
        diar_seconds = 0.0
        if job.has_speaker_labels:
            diar_seconds = max(base_seconds * self._diarization_speed_factor(job), 1.0)
        total_seconds = max(asr_seconds + diar_seconds, 1.0)
        return asr_seconds, diar_seconds, total_seconds

    def _estimate_total_seconds(self, job: Job, duration_hint: Optional[float] = None) -> int:
        """Estimate total processing time based on duration, model, and diarization."""
        _, _, total_seconds = self._estimate_stage_seconds(job, duration_hint=duration_hint)
        estimate = int(max(total_seconds, 60))
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

    async def _drain_progress_during_diarization(
        self,
        job_id: str,
        *,
        start_percent: int,
        end_percent: int,
        expected_seconds: float,
        interval: float = 2.0,
    ) -> None:
        """Advance progress during diarization using a time-based heuristic."""
        try:
            diar_start = datetime.utcnow()
            while True:
                await asyncio.sleep(interval)
                async with AsyncSessionLocal() as session:
                    job_obj = await session.get(Job, job_id)
                    if (
                        not job_obj
                        or job_obj.status != "processing"
                        or job_obj.progress_stage != "diarizing"
                    ):
                        return
                    elapsed = (datetime.utcnow() - diar_start).total_seconds()
                    denom = expected_seconds or 1.0
                    if elapsed > denom:
                        denom = elapsed * 1.25
                    ratio = min(max(elapsed / denom, 0.0), 1.0)
                    target = int(start_percent + ((end_percent - start_percent) * ratio))
                    job_obj.progress_percent = max(int(job_obj.progress_percent or 0), target)
                    job_obj.updated_at = datetime.utcnow()
                    await session.commit()
        except asyncio.CancelledError:
            return
        except Exception as exc:  # Best-effort, don't fail transcription for this
            logger.warning("Diarization progress updater failed for job %s: %s", job_id, exc)

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
        job.progress_percent = 0
        job.progress_stage = "loading_model"
        job.estimated_total_seconds = job.estimated_total_seconds or 180
        job.estimated_time_left = job.estimated_total_seconds
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 50
        job.progress_stage = "transcribing"
        job.estimated_time_left = 30
        job.updated_at = datetime.utcnow()
        await db.commit()

        await asyncio.sleep(0.2)

        job.progress_percent = 95
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

        if job.started_at:
            job.processing_seconds = int(job.processing_seconds or 0) + int(
                (datetime.utcnow() - job.started_at).total_seconds()
            )
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
