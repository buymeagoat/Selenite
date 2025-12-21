"""Application startup validation and health checks."""

import logging
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import Base, engine

# Import models so metadata is populated for create_all safeguards
from app.models import (
    job,  # noqa: F401
    model_provider,  # noqa: F401
    settings as settings_model,  # noqa: F401
    system_preferences,  # noqa: F401
    tag,  # noqa: F401
    transcript,  # noqa: F401
    user,  # noqa: F401
    user_settings,  # noqa: F401
)
from app.models.model_provider import ModelSet, ModelEntry
from app.models.system_preferences import SystemPreferences

logger = logging.getLogger("app.startup")

# Curated provider seed used as a last-resort guard if registry tables are empty.
_CURATED = {
    "asr": {
        "whisper": ["tiny", "base", "small", "medium", "large-v3"],
        "faster-whisper": ["tiny", "base", "medium-int8"],
        "wav2vec2": ["base-960h", "large-lv60"],
        "nemo": ["conformer-ctc-en"],
        "vosk": ["small-en-us", "large-en-us"],
        "coqui-stt": ["en-us"],
        "transformers": ["xls-r-300m", "wavlm-base"],
    },
    "diarizer": {
        "pyannote": ["diarization-3.1", "segmentation-3.0", "wespeaker-voxceleb-resnet34-LM"],
        "nemo-diarizer": ["offline"],
        "speechbrain": ["ecapa-diarization"],
        "resemblyzer": ["encoder-clustering"],
    },
}


async def ensure_core_tables() -> None:
    """
    Guardrail: ensure critical tables exist and seed minimal rows if missing.

    This is a safety net when the DB has been manually altered (e.g., tables dropped)
    but alembic is already at head. It is intentionally conservative and idempotent.
    """
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    async with AsyncSession(engine) as session:
        # Ensure system_preferences row exists
        pref = await session.get(SystemPreferences, 1)
        if not pref:
            logger.warning("Seeding default system_preferences row (id=1, UTC).")
            pref = SystemPreferences(
                id=1,
                server_time_zone="UTC",
                transcode_to_wav=True,
                enable_empty_weights=False,
            )
            session.add(pref)

        # If registry tables are empty (likely dropped), re-seed curated providers/entries
        set_count = (await session.execute(select(func.count(ModelSet.id)))).scalar_one()
        entry_count = (await session.execute(select(func.count(ModelEntry.id)))).scalar_one()
        if set_count == 0 and entry_count == 0:
            logger.warning(
                "Registry tables empty; re-seeding curated providers/entries as a guardrail."
            )
            models_root = Path(settings.model_storage_path)
            models_root.mkdir(parents=True, exist_ok=True)
            for ptype, providers in _CURATED.items():
                for provider, entries in providers.items():
                    set_path = (models_root / provider).resolve()
                    set_path.mkdir(parents=True, exist_ok=True)
                    model_set = ModelSet(
                        type=ptype,
                        name=provider,
                        description=f"Seeded {ptype} provider '{provider}' (weights not included).",
                        abs_path=str(set_path),
                        enabled=False,
                        disable_reason="Seeded provider; add weights to enable.",
                    )
                    session.add(model_set)
                    await session.flush()
                    for entry in entries:
                        entry_path = (set_path / entry).resolve()
                        entry_path.mkdir(parents=True, exist_ok=True)
                        session.add(
                            ModelEntry(
                                set_id=model_set.id,
                                type=ptype,
                                name=entry,
                                description=f"Seeded {ptype} entry '{entry}' (weights not included).",
                                abs_path=str(entry_path),
                                enabled=False,
                                disable_reason="Weights not present; drop files then enable.",
                            )
                        )

        await session.commit()


def validate_configuration() -> list[str]:
    """Validate application configuration.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate secret key in production
    if settings.is_production:
        if settings.secret_key == "dev-secret-key-change-in-production":
            errors.append(
                "SECRET_KEY is still set to default value in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        elif len(settings.secret_key) < 32:
            errors.append(
                f"SECRET_KEY is too short ({len(settings.secret_key)} chars). "
                "Use at least 32 characters in production."
            )

    # Validate CORS origins in production
    if settings.is_production:
        origins_lower = settings.cors_origins.lower()
        if not settings.allow_localhost_cors and (
            "localhost" in origins_lower or "127.0.0.1" in origins_lower
        ):
            errors.append(
                "CORS_ORIGINS contains localhost/127.0.0.1 in production. "
                "Configure production frontend URLs."
            )

    # Validate database URL
    if not settings.database_url:
        errors.append("DATABASE_URL is not configured")

    # Validate storage paths exist
    for path_name, path_value in [
        ("MEDIA_STORAGE_PATH", settings.media_storage_path),
        ("TRANSCRIPT_STORAGE_PATH", settings.transcript_storage_path),
    ]:
        path = Path(path_value)
        if not path.exists():
            logger.warning(f"{path_name} does not exist, will be created: {path}")
        elif not path.is_dir():
            errors.append(f"{path_name} is not a directory: {path}")

    # Validate model storage path
    model_path = Path(settings.model_storage_path)
    if not model_path.exists():
        errors.append(
            f"MODEL_STORAGE_PATH does not exist: {model_path}. "
            "Download Whisper models to 'backend/models' or update path."
        )

    # Warn if legacy backend/storage exists; canonical path is project-root /storage
    legacy_storage = Path(__file__).resolve().parents[2] / "storage"
    project_storage = Path(settings.media_storage_path).resolve().parents[0]
    if legacy_storage.exists() and legacy_storage.resolve() != project_storage:
        logger.warning(
            "Legacy storage directory detected at %s. Canonical storage root is %s. "
            "Do not place new files in the legacy path; migrate data to the canonical root.",
            legacy_storage,
            project_storage,
        )

    return errors


def validate_environment() -> list[str]:
    """Validate runtime environment requirements.

    Returns:
        List of validation warnings (not fatal)
    """
    warnings = []

    # Check for ffmpeg (required for whisper)
    try:
        import subprocess

        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            warnings.append("ffmpeg is not available or not working correctly")
    except FileNotFoundError:
        warnings.append(
            "ffmpeg is not installed. Required for audio/video processing. "
            "Install from https://ffmpeg.org/"
        )
    except Exception as e:
        warnings.append(f"Could not check ffmpeg: {e}")

    return warnings


async def run_startup_checks() -> None:
    """Run all startup validation checks.

    Raises:
        RuntimeError: If critical configuration errors are found
    """
    logger.info("Running startup validation checks...")

    # Guardrail: ensure tables exist and seed minimal rows if missing
    await ensure_core_tables()

    # Configuration validation (critical)
    config_errors = validate_configuration()
    if config_errors:
        logger.error("Configuration validation failed:")
        for error in config_errors:
            logger.error(f"  - {error}")
        raise RuntimeError(
            f"Configuration validation failed with {len(config_errors)} error(s). "
            "Fix configuration and restart."
        )

    logger.info("Configuration validation passed")

    # Environment validation (warnings only)
    env_warnings = validate_environment()
    if env_warnings:
        logger.warning("Environment checks found issues:")
        for warning in env_warnings:
            logger.warning(f"  - {warning}")
    else:
        logger.info("Environment validation passed")

    logger.info("Startup validation completed")
