"""Application configuration management."""

import os
import secrets
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Storage
    media_storage_path: str = "./storage/media"
    transcript_storage_path: str = "./storage/transcripts"
    model_storage_path: str = "models"

    # Transcription
    max_concurrent_jobs: int = 3
    default_whisper_model: str = "medium"
    default_language: str = "auto"

    # Server
    host: str = "0.0.0.0"
    port: int = 8100
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

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
        return self.environment == "testing"

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
        if env == "production" and ("localhost" in v.lower() or "127.0.0.1" in v):
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

    def generate_secure_secret(self) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_urlsafe(32)


# Global settings instance
settings = Settings()
if os.getenv("PYTEST_CURRENT_TEST"):
    settings.environment = "testing"
