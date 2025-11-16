"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./selenite.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Storage
    media_storage_path: str = "./storage/media"
    transcript_storage_path: str = "./storage/transcripts"
    model_storage_path: str = "../models"

    # Transcription
    max_concurrent_jobs: int = 3
    default_whisper_model: str = "medium"
    default_language: str = "auto"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
