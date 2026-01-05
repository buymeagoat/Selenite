"""add admin ASR/diarization settings

Revision ID: 20251125_admin_asr_diar
Revises: 4db27c61f220
Create Date: 2025-11-25 12:15:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251125_admin_asr_diar"
down_revision: Union[str, None] = "4db27c61f220"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_settings")}

    if "default_diarizer" not in cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "default_diarizer", sa.String(length=20), nullable=False, server_default="vad"
            ),
        )
    if "diarization_enabled" not in cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "diarization_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )
    if "allow_job_overrides" not in cols:
        op.add_column(
            "user_settings",
            sa.Column(
                "allow_job_overrides", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("user_settings", "default_diarizer", server_default=None)
        op.alter_column("user_settings", "diarization_enabled", server_default=None)
        op.alter_column("user_settings", "allow_job_overrides", server_default=None)

    job_cols = {c["name"] for c in inspector.get_columns("jobs")}
    if "diarizer_used" not in job_cols:
        op.add_column("jobs", sa.Column("diarizer_used", sa.String(length=20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_settings")}

    if "allow_job_overrides" in cols:
        op.drop_column("user_settings", "allow_job_overrides")
    if "diarization_enabled" in cols:
        op.drop_column("user_settings", "diarization_enabled")
    if "default_diarizer" in cols:
        op.drop_column("user_settings", "default_diarizer")

    job_cols = {c["name"] for c in inspector.get_columns("jobs")}
    if "diarizer_used" in job_cols:
        op.drop_column("jobs", "diarizer_used")
