"""Access control helpers for job scoping."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_settings import UserSettings


async def should_include_all_jobs(current_user: User, db: AsyncSession) -> bool:
    """Return True when admin has opted to view all jobs."""
    if not current_user.is_admin:
        return False
    result = await db.execute(
        select(UserSettings.show_all_jobs).where(UserSettings.user_id == current_user.id)
    )
    row = result.first()
    if not row:
        return False
    return bool(row[0])
