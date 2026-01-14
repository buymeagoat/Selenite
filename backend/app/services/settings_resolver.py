"""Shared helpers for resolving admin/user defaults."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_settings import UserSettings


def _same_optional(left: str | None, right: str | None) -> bool:
    return (left or "") == (right or "")


def compute_use_admin_asr_defaults(
    user_settings: UserSettings, admin_settings: UserSettings | None
) -> bool:
    if not admin_settings:
        return False
    return (
        _same_optional(user_settings.default_asr_provider, admin_settings.default_asr_provider)
        and user_settings.default_model == admin_settings.default_model
        and user_settings.default_language == admin_settings.default_language
        and bool(user_settings.enable_timestamps) == bool(admin_settings.enable_timestamps)
    )


def compute_use_admin_diarizer_defaults(
    user_settings: UserSettings, admin_settings: UserSettings | None
) -> bool:
    if not admin_settings:
        return False
    return (
        _same_optional(
            user_settings.default_diarizer_provider, admin_settings.default_diarizer_provider
        )
        and user_settings.default_diarizer == admin_settings.default_diarizer
        and bool(user_settings.diarization_enabled) == bool(admin_settings.diarization_enabled)
    )


async def get_admin_settings(db: AsyncSession) -> UserSettings | None:
    stmt = (
        select(UserSettings)
        .join(User, UserSettings.user_id == User.id)
        .where(User.is_admin.is_(True), User.is_disabled.is_(False))
        .order_by(UserSettings.updated_at.desc(), UserSettings.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    result = await db.execute(
        select(User)
        .where(User.is_admin.is_(True), User.is_disabled.is_(False))
        .order_by(User.id.asc())
    )
    admin_user = result.scalars().first()
    if not admin_user:
        return None
    return await get_or_create_settings(admin_user, db)


async def get_or_create_settings(current_user: User, db: AsyncSession) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        if current_user.is_admin:
            settings.show_all_jobs = True
        if not current_user.is_admin:
            admin_settings = await get_admin_settings(db)
            if admin_settings:
                settings.default_asr_provider = admin_settings.default_asr_provider
                settings.default_model = admin_settings.default_model
                settings.default_language = admin_settings.default_language
                settings.default_diarizer_provider = admin_settings.default_diarizer_provider
                settings.default_diarizer = admin_settings.default_diarizer
                settings.diarization_enabled = admin_settings.diarization_enabled
                settings.enable_timestamps = admin_settings.enable_timestamps
                settings.max_concurrent_jobs = admin_settings.max_concurrent_jobs
            settings.use_admin_asr_defaults = True
            settings.use_admin_diarizer_defaults = True
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    if current_user.is_admin and not settings.show_all_jobs_set and not settings.show_all_jobs:
        settings.show_all_jobs = True
        await db.commit()
        await db.refresh(settings)
    return settings


def build_effective_defaults(
    user_settings: UserSettings | None, admin_settings: UserSettings | None
) -> dict[str, Any]:
    if not user_settings and not admin_settings:
        return {
            "default_asr_provider": None,
            "default_model": None,
            "default_language": None,
            "default_diarizer_provider": None,
            "default_diarizer": None,
            "diarization_enabled": False,
            "enable_timestamps": True,
            "allow_asr_overrides": False,
            "allow_diarizer_overrides": False,
        }
    base = user_settings or admin_settings
    if not base:
        raise RuntimeError("Missing settings to resolve defaults.")

    if not admin_settings:
        return {
            "default_asr_provider": base.default_asr_provider,
            "default_model": base.default_model,
            "default_language": base.default_language,
            "default_diarizer_provider": base.default_diarizer_provider,
            "default_diarizer": base.default_diarizer,
            "diarization_enabled": base.diarization_enabled,
            "enable_timestamps": base.enable_timestamps,
            "allow_asr_overrides": base.allow_asr_overrides,
            "allow_diarizer_overrides": base.allow_diarizer_overrides,
        }

    allow_asr_overrides = admin_settings.allow_asr_overrides
    allow_diarizer_overrides = admin_settings.allow_diarizer_overrides

    use_admin_asr_defaults = True
    use_admin_diarizer_defaults = True
    if user_settings and allow_asr_overrides:
        use_admin_asr_defaults = user_settings.use_admin_asr_defaults
    if user_settings and allow_diarizer_overrides:
        use_admin_diarizer_defaults = user_settings.use_admin_diarizer_defaults

    asr_source = admin_settings if use_admin_asr_defaults else base
    diar_source = admin_settings if use_admin_diarizer_defaults else base

    return {
        "default_asr_provider": asr_source.default_asr_provider,
        "default_model": asr_source.default_model,
        "default_language": asr_source.default_language,
        "default_diarizer_provider": diar_source.default_diarizer_provider,
        "default_diarizer": diar_source.default_diarizer,
        "diarization_enabled": diar_source.diarization_enabled,
        "enable_timestamps": asr_source.enable_timestamps,
        "allow_asr_overrides": allow_asr_overrides,
        "allow_diarizer_overrides": allow_diarizer_overrides,
    }


def build_effective_user_settings(
    user_settings: UserSettings | None, admin_settings: UserSettings | None
) -> SimpleNamespace | None:
    if not user_settings and not admin_settings:
        return None
    effective = build_effective_defaults(user_settings, admin_settings)
    return SimpleNamespace(
        default_asr_provider=effective["default_asr_provider"],
        default_model=effective["default_model"],
        default_language=effective["default_language"],
        default_diarizer_provider=effective["default_diarizer_provider"],
        default_diarizer=effective["default_diarizer"],
        diarization_enabled=effective["diarization_enabled"],
        enable_timestamps=effective["enable_timestamps"],
        allow_asr_overrides=effective["allow_asr_overrides"],
        allow_diarizer_overrides=effective["allow_diarizer_overrides"],
    )
