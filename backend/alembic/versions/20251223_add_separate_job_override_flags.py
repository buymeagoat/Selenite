"""Add separate per-job override flags for ASR and diarization.

Revision ID: 20251223_add_separate_job_override_flags
Revises: 20251220_add_enable_empty_weights
Create Date: 2025-12-23 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251223_add_separate_job_override_flags"
down_revision = "20251220_add_enable_empty_weights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_settings" not in inspector.get_table_names():
        from app.models.user_settings import UserSettings  # local import

        UserSettings.__table__.create(bind, checkfirst=True)
        return
    cols = {col["name"] for col in inspector.get_columns("user_settings")}
    with op.batch_alter_table("user_settings") as batch_op:
        if "allow_asr_overrides" not in cols:
            batch_op.add_column(
                sa.Column(
                    "allow_asr_overrides",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "allow_diarizer_overrides" not in cols:
            batch_op.add_column(
                sa.Column(
                    "allow_diarizer_overrides",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
    if "allow_job_overrides" in cols:
        op.execute(
            sa.text(
                """
                UPDATE user_settings
                SET allow_asr_overrides = allow_job_overrides,
                    allow_diarizer_overrides = allow_job_overrides
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_settings" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'user_settings'. Cannot downgrade overrides.")
    cols = {col["name"] for col in inspector.get_columns("user_settings")}
    with op.batch_alter_table("user_settings") as batch_op:
        if "allow_diarizer_overrides" in cols:
            batch_op.drop_column("allow_diarizer_overrides")
        if "allow_asr_overrides" in cols:
            batch_op.drop_column("allow_asr_overrides")
