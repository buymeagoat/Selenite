"""Application startup validation and health checks."""

import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger("app.startup")


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
