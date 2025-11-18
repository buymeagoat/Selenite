"""Tests for startup validation and configuration checks."""

from unittest.mock import patch

from app.startup_checks import validate_configuration, validate_environment


def test_validate_configuration_development():
    """Test configuration validation passes in development."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = False
        mock_settings.secret_key = "dev-secret-key-change-in-production"
        mock_settings.cors_origins = "http://localhost:5173"
        mock_settings.database_url = "sqlite+aiosqlite:///./test.db"
        mock_settings.media_storage_path = "./storage/media"
        mock_settings.transcript_storage_path = "./storage/transcripts"
        mock_settings.model_storage_path = "models"

        errors = validate_configuration()

        # No errors in development with default values
        assert len(errors) == 0


def test_validate_configuration_production_default_secret():
    """Test configuration validation fails in production with default secret."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "dev-secret-key-change-in-production"
        mock_settings.cors_origins = "https://example.com"
        mock_settings.database_url = "postgresql://..."
        mock_settings.media_storage_path = "/var/lib/selenite/media"
        mock_settings.transcript_storage_path = "/var/lib/selenite/transcripts"
        mock_settings.model_storage_path = "models"

        errors = validate_configuration()

        # Should have error about default secret key
        assert len(errors) >= 1
        assert any("SECRET_KEY" in error for error in errors)


def test_validate_configuration_production_short_secret():
    """Test configuration validation fails with short secret key."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "too-short"
        mock_settings.cors_origins = "https://example.com"
        mock_settings.database_url = "postgresql://..."
        mock_settings.media_storage_path = "/var/lib/selenite/media"
        mock_settings.transcript_storage_path = "/var/lib/selenite/transcripts"
        mock_settings.model_storage_path = "models"

        errors = validate_configuration()

        # Should have error about short secret key
        assert len(errors) >= 1
        assert any("too short" in error for error in errors)


def test_validate_configuration_production_localhost_cors():
    """Test configuration validation fails with localhost in CORS for production."""
    with patch("app.startup_checks.settings") as mock_settings:
        mock_settings.is_production = True
        mock_settings.secret_key = "a" * 32  # Long enough
        mock_settings.cors_origins = "http://localhost:5173,https://example.com"
        mock_settings.database_url = "postgresql://..."
        mock_settings.media_storage_path = "/var/lib/selenite/media"
        mock_settings.transcript_storage_path = "/var/lib/selenite/transcripts"
        mock_settings.model_storage_path = "models"

        errors = validate_configuration()

        # Should have error about localhost in CORS
        assert len(errors) >= 1
        assert any("localhost" in error.lower() for error in errors)


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
