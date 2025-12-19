"""Settings routes: get and update user transcription preferences."""

import logging
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.routes.auth import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.system_preferences import SystemPreferences
from app.models.model_provider import ModelEntry, ModelSet
from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateAsr,
    SettingsUpdateDiarization,
)
from app.services.job_queue import queue

router = APIRouter(prefix="/settings", tags=["settings"])

logger = logging.getLogger(__name__)


async def _get_or_create_settings(current_user: User, db: AsyncSession) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def _get_system_preferences(db: AsyncSession) -> SystemPreferences:
    result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
    prefs = result.scalar_one_or_none()
    if not prefs:
        # Try to derive a sensible default from the server's local timezone; fall back to UTC.
        try:
            import datetime as _dt

            local_tz = _dt.datetime.now().astimezone().tzinfo
            default_tz = (
                getattr(local_tz, "key", None) or getattr(local_tz, "zone", None) or str(local_tz)
            )
        except Exception:
            default_tz = "UTC"

        if not default_tz or "/" not in default_tz:
            default_tz = "UTC"

        prefs = SystemPreferences(id=1, server_time_zone=default_tz, transcode_to_wav=True)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


def _validate_timezone(value: str | None) -> str | None:
    if not value:
        return None
    try:
        ZoneInfo(value)
    except Exception as exc:
        # On platforms without tzdata (e.g., some Windows envs), accept the string to avoid blocking.
        logger.warning("Timezone validation fallback for '%s': %s", value, exc)
        return value
    return value


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_settings = await _get_or_create_settings(current_user, db)
    prefs = await _get_system_preferences(db)
    return SettingsResponse(
        default_asr_provider=user_settings.default_asr_provider,
        default_model=user_settings.default_model,
        default_language=user_settings.default_language,
        default_diarizer_provider=user_settings.default_diarizer_provider,
        default_diarizer=user_settings.default_diarizer,
        diarization_enabled=user_settings.diarization_enabled,
        allow_job_overrides=user_settings.allow_job_overrides,
        enable_timestamps=user_settings.enable_timestamps,
        max_concurrent_jobs=user_settings.max_concurrent_jobs,
        time_zone=user_settings.time_zone,
        server_time_zone=prefs.server_time_zone,
        transcode_to_wav=prefs.transcode_to_wav,
        last_selected_asr_set=user_settings.last_selected_asr_set,
        last_selected_diarizer_set=user_settings.last_selected_diarizer_set,
    )


async def _apply_settings(
    payload: SettingsUpdateRequest,
    current_user: User,
    db: AsyncSession,
) -> SettingsResponse:
    user_settings = await _get_or_create_settings(current_user, db)
    system_prefs = await _get_system_preferences(db)

    async def _entry_exists(name: str, provider_type: str, provider: str | None = None) -> bool:
        stmt = (
            select(ModelEntry)
            .join(ModelSet)
            .where(ModelSet.type == provider_type)
            .where(ModelEntry.name == name)
        )
        if provider:
            stmt = stmt.where(ModelSet.name == provider)
        result = await db.execute(stmt.limit(1))
        return result.scalars().first() is not None

    async def _set_exists(name: str, provider_type: str) -> bool:
        stmt = select(ModelSet).where(ModelSet.type == provider_type, ModelSet.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _resolve_entry_provider(
        name: str, provider_type: str, provider: str | None = None
    ) -> str | None:
        stmt = (
            select(ModelSet.name)
            .join(ModelEntry)
            .where(ModelSet.type == provider_type)
            .where(ModelEntry.name == name)
        )
        if provider:
            stmt = stmt.where(ModelSet.name == provider)
        result = await db.execute(stmt.limit(1))
        return result.scalars().first()

    diarization_enabled_next = (
        payload.diarization_enabled
        if payload.diarization_enabled is not None
        else user_settings.diarization_enabled
    )

    if payload.default_model:
        exists = await _entry_exists(payload.default_model, "asr", payload.default_asr_provider)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default ASR model must reference an existing registry entry.",
            )

    resolved_diarizer_provider: str | None = None
    if diarization_enabled_next:
        if payload.default_diarizer:
            provider_hint = (
                payload.default_diarizer_provider
                if payload.default_diarizer_provider is not None
                else user_settings.default_diarizer_provider
            )
            resolved_diarizer_provider = await _resolve_entry_provider(
                payload.default_diarizer, "diarizer", provider_hint
            )
            if not resolved_diarizer_provider:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Default diarizer must reference an existing registry entry.",
                )
        if payload.default_diarizer_provider:
            exists = await _set_exists(payload.default_diarizer_provider, "diarizer")
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Default diarizer provider must reference an existing registry provider.",
                )
    else:
        # Diarization is off; clear default_diarizer so stale values don't block ASR defaults.
        payload.default_diarizer = None
        payload.default_diarizer_provider = None

    # Allow clearing defaults explicitly (None) so stale defaults don't linger
    if payload.default_asr_provider is not None:
        user_settings.default_asr_provider = payload.default_asr_provider
    if payload.default_model is not None:
        user_settings.default_model = payload.default_model
    if payload.default_language is not None:
        user_settings.default_language = payload.default_language or user_settings.default_language
    # Respect non-null constraint on default_diarizer: when diarization is off, keep existing value but it is ignored;
    # when turning it off, ensure we do not write NULL.
    if diarization_enabled_next:
        user_settings.default_diarizer = (
            payload.default_diarizer or user_settings.default_diarizer or "vad"
        )
        if resolved_diarizer_provider is not None:
            user_settings.default_diarizer_provider = resolved_diarizer_provider
        elif payload.default_diarizer_provider is not None:
            user_settings.default_diarizer_provider = payload.default_diarizer_provider or None
    else:
        user_settings.default_diarizer = user_settings.default_diarizer or "vad"
        user_settings.default_diarizer_provider = None
    user_settings.diarization_enabled = diarization_enabled_next
    user_settings.allow_job_overrides = (
        payload.allow_job_overrides
        if payload.allow_job_overrides is not None
        else user_settings.allow_job_overrides
    )
    user_settings.enable_timestamps = (
        payload.enable_timestamps
        if payload.enable_timestamps is not None
        else user_settings.enable_timestamps
    )
    user_settings.max_concurrent_jobs = (
        payload.max_concurrent_jobs
        if payload.max_concurrent_jobs is not None
        else user_settings.max_concurrent_jobs
    )
    if payload.time_zone is not None:
        user_settings.time_zone = _validate_timezone(payload.time_zone)
    if payload.last_selected_asr_set is not None:
        if payload.last_selected_asr_set and not await _set_exists(
            payload.last_selected_asr_set, "asr"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last selected ASR set must reference an existing provider.",
            )
        user_settings.last_selected_asr_set = payload.last_selected_asr_set
    if payload.last_selected_diarizer_set is not None:
        if payload.last_selected_diarizer_set and not await _set_exists(
            payload.last_selected_diarizer_set, "diarizer"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last selected diarizer set must reference an existing provider.",
            )
        user_settings.last_selected_diarizer_set = payload.last_selected_diarizer_set
    logger.info(
        "Settings updated for user %s: last_selected_asr_set=%s last_selected_diarizer_set=%s",
        current_user.id,
        user_settings.last_selected_asr_set,
        user_settings.last_selected_diarizer_set,
    )
    if payload.server_time_zone is not None:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins may update the server time zone.",
            )
        system_prefs.server_time_zone = (
            _validate_timezone(payload.server_time_zone) or system_prefs.server_time_zone
        )
        system_prefs.touch()
    if payload.transcode_to_wav is not None:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins may update media transcoding settings.",
            )
        system_prefs.transcode_to_wav = bool(payload.transcode_to_wav)
        system_prefs.touch()

    user_settings.touch()
    await db.commit()
    await db.refresh(user_settings)
    await db.refresh(system_prefs)
    if not settings.is_testing:
        try:
            await queue.set_concurrency(user_settings.max_concurrent_jobs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return SettingsResponse(
        default_asr_provider=user_settings.default_asr_provider,
        default_model=user_settings.default_model,
        default_language=user_settings.default_language,
        default_diarizer_provider=user_settings.default_diarizer_provider,
        default_diarizer=user_settings.default_diarizer,
        diarization_enabled=user_settings.diarization_enabled,
        allow_job_overrides=user_settings.allow_job_overrides,
        enable_timestamps=user_settings.enable_timestamps,
        max_concurrent_jobs=user_settings.max_concurrent_jobs,
        time_zone=user_settings.time_zone,
        server_time_zone=system_prefs.server_time_zone,
        transcode_to_wav=system_prefs.transcode_to_wav,
        last_selected_asr_set=user_settings.last_selected_asr_set,
        last_selected_diarizer_set=user_settings.last_selected_diarizer_set,
    )


@router.put("/asr", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def update_settings_asr(
    payload: SettingsUpdateAsr,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update ASR defaults without touching diarization settings."""

    user_settings = await _get_or_create_settings(current_user, db)
    base_payload = SettingsUpdateRequest(
        default_asr_provider=payload.default_asr_provider,
        default_model=payload.default_model,
        default_language=payload.default_language,
        allow_job_overrides=payload.allow_job_overrides,
        enable_timestamps=payload.enable_timestamps,
        max_concurrent_jobs=payload.max_concurrent_jobs,
        default_diarizer=user_settings.default_diarizer,
        diarization_enabled=user_settings.diarization_enabled,
        last_selected_asr_set=payload.last_selected_asr_set,
        last_selected_diarizer_set=user_settings.last_selected_diarizer_set,
    )
    return await _apply_settings(base_payload, current_user, db)


@router.put("/diarization", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def update_settings_diarization(
    payload: SettingsUpdateDiarization,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update diarization defaults without touching ASR settings."""

    user_settings = await _get_or_create_settings(current_user, db)
    base_payload = SettingsUpdateRequest(
        default_model=user_settings.default_model,
        default_language=user_settings.default_language,
        allow_job_overrides=(
            payload.allow_job_overrides
            if payload.allow_job_overrides is not None
            else user_settings.allow_job_overrides
        ),
        enable_timestamps=user_settings.enable_timestamps,
        max_concurrent_jobs=user_settings.max_concurrent_jobs,
        default_diarizer=payload.default_diarizer,
        diarization_enabled=payload.diarization_enabled,
        default_asr_provider=user_settings.default_asr_provider,
        last_selected_asr_set=user_settings.last_selected_asr_set,
        last_selected_diarizer_set=payload.last_selected_diarizer_set,
    )
    return await _apply_settings(base_payload, current_user, db)


@router.put("", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def update_settings(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await _apply_settings(payload, current_user, db)
    except HTTPException as exc:
        logger.error("Failed to update settings: %s | payload=%s", exc.detail, payload.model_dump())
        raise
