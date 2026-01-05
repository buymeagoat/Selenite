"""Add default_tags_seeded to system_preferences.

Revision ID: 20251227_add_default_tags_seeded
Revises: 20251223_add_separate_job_override_flags
Create Date: 2025-12-27 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251227_add_default_tags_seeded"
down_revision = "20251223_add_separate_job_override_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_preferences" not in inspector.get_table_names():
        from app.models.system_preferences import SystemPreferences

        SystemPreferences.__table__.create(bind, checkfirst=True)
        return
    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "default_tags_seeded" not in cols:
            batch_op.add_column(
                sa.Column(
                    "default_tags_seeded", sa.Boolean(), nullable=False, server_default=sa.text("0")
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_preferences" not in inspector.get_table_names():
        raise RuntimeError(
            "Missing required table 'system_preferences'. Cannot downgrade default_tags_seeded."
        )
    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "default_tags_seeded" in cols:
            batch_op.drop_column("default_tags_seeded")
