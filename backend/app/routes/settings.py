"""Settings routes: get and update user transcription preferences."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.routes.auth import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.job_queue import queue

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_settings(current_user: User, db: AsyncSession) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_settings = await _get_or_create_settings(current_user, db)
    return SettingsResponse(
        default_model=user_settings.default_model,
        default_language=user_settings.default_language,
        max_concurrent_jobs=user_settings.max_concurrent_jobs,
    )


@router.put("", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def update_settings(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_settings = await _get_or_create_settings(current_user, db)
    user_settings.default_model = payload.default_model
    user_settings.default_language = payload.default_language
    user_settings.max_concurrent_jobs = payload.max_concurrent_jobs
    user_settings.touch()
    await db.commit()
    await db.refresh(user_settings)
    if not settings.is_testing:
        try:
            await queue.set_concurrency(user_settings.max_concurrent_jobs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return SettingsResponse(
        default_model=user_settings.default_model,
        default_language=user_settings.default_language,
        max_concurrent_jobs=user_settings.max_concurrent_jobs,
    )
