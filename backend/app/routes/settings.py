"""Settings routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.user import User
from app.models.settings import Settings
from app.models.job import Job

router = APIRouter(tags=["settings"])

# Valid Whisper models
VALID_MODELS = ["tiny", "base", "small", "medium", "large", "large-v3"]

# Common language codes (ISO 639-1 + auto)
VALID_LANGUAGES = [
    "auto",
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "ja",
    "zh",
    "ko",
    "ar",
    "hi",
    "nl",
    "pl",
    "tr",
    "sv",
    "da",
    "no",
    "fi",
]


class SettingsUpdate(BaseModel):
    """Settings update request."""

    default_model: str | None = Field(None, min_length=1, max_length=20)
    default_language: str | None = Field(None, min_length=2, max_length=10)
    default_timestamps: bool | None = None
    default_speaker_detection: bool | None = None
    max_concurrent_jobs: int | None = Field(None, ge=1, le=10)


class SettingsResponse(BaseModel):
    """Settings response."""

    default_model: str
    default_language: str
    default_timestamps: bool
    default_speaker_detection: bool
    max_concurrent_jobs: int
    storage_location: str
    storage_used_bytes: int
    storage_limit_bytes: int


class SettingsUpdateResponse(BaseModel):
    """Settings update response."""

    message: str
    settings: SettingsResponse


async def get_or_create_settings(db: AsyncSession, user_id: int) -> Settings:
    """Get or create default settings for a user."""
    stmt = select(Settings).where(Settings.user_id == user_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = Settings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


async def calculate_storage_used(db: AsyncSession, user_id: int) -> int:
    """Calculate total storage used by user's jobs."""
    stmt = select(func.sum(Job.file_size)).where(Job.user_id == user_id)
    result = await db.execute(stmt)
    total = result.scalar()
    return total or 0


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user settings.

    Returns all user settings including storage information.
    Creates default settings if they don't exist.
    """
    settings = await get_or_create_settings(db, current_user.id)
    storage_used = await calculate_storage_used(db, current_user.id)

    return SettingsResponse(
        default_model=settings.default_model,
        default_language=settings.default_language,
        default_timestamps=settings.default_timestamps,
        default_speaker_detection=settings.default_speaker_detection,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        storage_location=settings.storage_location,
        storage_used_bytes=storage_used,
        storage_limit_bytes=settings.storage_limit_bytes,
    )


@router.put("/settings", response_model=SettingsUpdateResponse)
async def update_settings(
    settings_update: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user settings.

    All fields are optional. Only provided fields will be updated.
    Validates model names and language codes.
    """
    # Validate model name
    if settings_update.default_model is not None:
        if settings_update.default_model not in VALID_MODELS:
            raise HTTPException(
                status_code=400, detail=f"Invalid model. Must be one of: {', '.join(VALID_MODELS)}"
            )

    # Validate language code
    if settings_update.default_language is not None:
        if settings_update.default_language not in VALID_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail="Invalid language code. Must be one of common ISO 639-1 codes or 'auto'",
            )

    # Get or create settings
    settings = await get_or_create_settings(db, current_user.id)

    # Update provided fields
    if settings_update.default_model is not None:
        settings.default_model = settings_update.default_model
    if settings_update.default_language is not None:
        settings.default_language = settings_update.default_language
    if settings_update.default_timestamps is not None:
        settings.default_timestamps = settings_update.default_timestamps
    if settings_update.default_speaker_detection is not None:
        settings.default_speaker_detection = settings_update.default_speaker_detection
    if settings_update.max_concurrent_jobs is not None:
        settings.max_concurrent_jobs = settings_update.max_concurrent_jobs

    await db.commit()
    await db.refresh(settings)

    # Calculate storage for response
    storage_used = await calculate_storage_used(db, current_user.id)

    return SettingsUpdateResponse(
        message="Settings updated successfully",
        settings=SettingsResponse(
            default_model=settings.default_model,
            default_language=settings.default_language,
            default_timestamps=settings.default_timestamps,
            default_speaker_detection=settings.default_speaker_detection,
            max_concurrent_jobs=settings.max_concurrent_jobs,
            storage_location=settings.storage_location,
            storage_used_bytes=storage_used,
            storage_limit_bytes=settings.storage_limit_bytes,
        ),
    )
