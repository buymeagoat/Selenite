"""Tests for startup validation and configuration checks."""

from unittest.mock import patch

import pytest

from app.startup_checks import validate_configuration, validate_environment, run_startup_checks


def _configure_paths(mock_settings, tmp_path):
    """Helper to point storage/model paths at existing temp directories."""
    media_dir = tmp_path / "media"
    transcripts_dir = tmp_path / "transcripts"
    models_dir = tmp_path / "models"
    media_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    mock_settings.media_storage_path = str(media_dir)
    mock_settings.transcript_storage_path = str(transcripts_dir)
    mock_settings.model_storage_path = str(models_dir)


def test_validate_configuration_development(tmp_path):
    """Test configuration validation passes in development."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = False
        mock_settings.secret_key = "dev-secret-key-change-in-production"
        mock_settings.cors_origins = "http://localhost:5173"
        mock_settings.database_url = "sqlite+aiosqlite:///./test.db"
        _configure_paths(mock_settings, tmp_path)

        errors = validate_configuration()

        # No errors in development with default values
        assert len(errors) == 0


def test_validate_configuration_production_default_secret(tmp_path):
    """Test configuration validation fails in production with default secret."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "dev-secret-key-change-in-production"
        mock_settings.cors_origins = "https://example.com"
        mock_settings.database_url = "postgresql://..."
        _configure_paths(mock_settings, tmp_path)

        errors = validate_configuration()

        # Should have error about default secret key
        assert len(errors) >= 1
        assert any("SECRET_KEY" in error for error in errors)


def test_validate_configuration_production_short_secret(tmp_path):
    """Test configuration validation fails with short secret key."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "too-short"
        mock_settings.cors_origins = "https://example.com"
        mock_settings.database_url = "postgresql://..."
        _configure_paths(mock_settings, tmp_path)

        errors = validate_configuration()

        # Should have error about short secret key
        assert len(errors) >= 1
        assert any("too short" in error for error in errors)


def test_validate_configuration_production_localhost_cors(tmp_path):
    """Test configuration validation fails with localhost in CORS for production."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "a" * 32  # Long enough
        mock_settings.cors_origins = "http://localhost:5173,https://example.com"
        mock_settings.database_url = "postgresql://..."
        _configure_paths(mock_settings, tmp_path)
        mock_settings.allow_localhost_cors = False

        errors = validate_configuration()

        # Should have error about localhost in CORS
        assert len(errors) >= 1
        assert any("localhost" in error.lower() for error in errors)


def test_validate_configuration_production_localhost_cors_allowed(tmp_path):
    """Test allowing localhost origins in production when explicitly enabled."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "a" * 32
        mock_settings.cors_origins = "http://localhost:5173,https://example.com"
        mock_settings.database_url = "postgresql://..."
        _configure_paths(mock_settings, tmp_path)
        mock_settings.allow_localhost_cors = True

        errors = validate_configuration()

        assert errors == []


def test_validate_environment_ffmpeg_missing():
    """Test environment validation detects missing ffmpeg."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        warnings = validate_environment()

        # Should warn about missing ffmpeg
        assert len(warnings) >= 1
        assert any("ffmpeg" in warning.lower() for warning in warnings)


def test_validate_environment_ffmpeg_present():
    """Test environment validation passes with ffmpeg installed."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        warnings = validate_environment()

        # Should have no warnings
        assert len(warnings) == 0


@pytest.mark.asyncio
async def test_run_startup_checks_success(monkeypatch):
    """run_startup_checks should exit quietly when no errors/warnings."""
    monkeypatch.setattr("app.startup_checks.validate_configuration", lambda: [])
    monkeypatch.setattr("app.startup_checks.validate_environment", lambda: [])

    await run_startup_checks()


@pytest.mark.asyncio
async def test_run_startup_checks_with_env_warnings(monkeypatch):
    """Environment warnings should not raise errors."""
    monkeypatch.setattr("app.startup_checks.validate_configuration", lambda: [])
    monkeypatch.setattr("app.startup_checks.validate_environment", lambda: ["ffmpeg missing"])

    await run_startup_checks()


@pytest.mark.asyncio
async def test_run_startup_checks_config_error(monkeypatch):
    """Configuration errors should raise RuntimeError."""
    monkeypatch.setattr(
        "app.startup_checks.validate_configuration",
        lambda: ["SECRET_KEY missing"],
    )
    monkeypatch.setattr("app.startup_checks.validate_environment", lambda: [])

    with pytest.raises(RuntimeError):
        await run_startup_checks()
