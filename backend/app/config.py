"""Application configuration management."""

import os
import secrets
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
STORAGE_ROOT = PROJECT_ROOT / "storage"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: Literal["development", "production", "testing"] = "development"

    # Database
    database_url: str = "sqlite+aiosqlite:///./selenite.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    admin_default_password: str | None = None

    # Storage
    media_storage_path: str = str(STORAGE_ROOT / "media")
    transcript_storage_path: str = str(STORAGE_ROOT / "transcripts")
    model_storage_path: str = str(BACKEND_ROOT / "models")
    nginx_ssl_cert_path: str | None = None
    nginx_ssl_key_path: str | None = None

    # Transcription
    max_concurrent_jobs: int = 3
    default_whisper_model: str = "medium"
    default_language: str = "auto"
    default_estimated_duration_seconds: int = 600
    stall_timeout_multiplier: float = 2.0
    stall_timeout_min_seconds: int = 300
    stall_check_interval_seconds: int = 20

    # E2E/automation helpers
    e2e_fast_transcription: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8100
    allow_localhost_cors: bool = False
    frontend_url: str | None = None
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:3000"
    )
    redis_url: str | None = None

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=(".env.test", ".env"), case_sensitive=False)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        env_var = os.getenv("ENVIRONMENT", "").lower() == "testing"
        pytest_flag = bool(os.getenv("PYTEST_CURRENT_TEST"))
        return self.environment == "testing" or env_var or pytest_flag

    @model_validator(mode="before")
    @classmethod
    def auto_allow_localhost(cls, values: dict) -> dict:
        """Automatically enable localhost CORS when binding to loopback hosts in production."""
        env = (values.get("environment") or "development").lower()
        host = (values.get("host") or "").lower()
        allow_local = values.get("allow_localhost_cors", False)

        host_is_loopback = host in LOOPBACK_HOSTS or host.startswith("127.")
        if env == "production" and not allow_local and host_is_loopback:
            values["allow_localhost_cors"] = True
        return values

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate secret key is secure in production."""
        # Check if environment is production (need to get from values dict)
        env = info.data.get("environment", "development")
        if env == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY must be changed from default value in production. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if env == "production" and len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters in production for security. "
                f"Current length: {len(v)}"
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """Validate CORS origins are properly configured in production."""
        env = info.data.get("environment", "development")
        allow_local = info.data.get("allow_localhost_cors", False)
        host = info.data.get("host", "").lower()
        host_is_loopback = host in LOOPBACK_HOSTS or host.startswith("127.")
        if (
            env == "production"
            and not allow_local
            and not host_is_loopback
            and ("localhost" in v.lower() or "127.0.0.1" in v)
        ):
            raise ValueError(
                "CORS_ORIGINS should not include localhost in production. "
                "Configure production frontend URLs."
            )
        return v

    @model_validator(mode="after")
    def validate_storage_paths(self) -> "Settings":
        """Ensure storage directories exist."""
        for path_attr in ["media_storage_path", "transcript_storage_path"]:
            path = Path(getattr(self, path_attr))
            path.mkdir(parents=True, exist_ok=True)
        return self

    @model_validator(mode="after")
    def normalize_database_path(self) -> "Settings":
        """Ensure SQLite URLs point to backend/ regardless of CWD."""
        try:
            url = make_url(self.database_url)
        except Exception:
            return self

        if not url.get_backend_name().startswith("sqlite"):
            return self

        db_path = url.database
        if not db_path:
            return self

        path_obj = Path(db_path)
        if not path_obj.is_absolute():
            abs_path = (BACKEND_ROOT / path_obj).resolve()
            url = url.set(database=str(abs_path))
            self.database_url = str(url)
        return self

    def generate_secure_secret(self) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_urlsafe(32)


# Global settings instance
settings = Settings()
if os.getenv("PYTEST_CURRENT_TEST"):
    settings.environment = "testing"
if settings.is_testing:
    settings.environment = "testing"
    if not settings.database_url.startswith("sqlite+aiosqlite"):
        settings.database_url = "sqlite+aiosqlite:///./selenite.db"
