"""Add date/time display preferences to user_settings.

Revision ID: 20260119_add_user_datetime_prefs
Revises: 20260112_add_user_default_override_flags
Create Date: 2026-01-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260119_add_user_datetime_prefs"
down_revision = "20260112_add_user_default_override_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("date_format", sa.String(length=20), server_default="locale", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("time_format", sa.String(length=20), server_default="locale", nullable=False),
    )
    op.add_column(
        "user_settings",
        sa.Column("locale", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "locale")
    op.drop_column("user_settings", "time_format")
    op.drop_column("user_settings", "date_format")
