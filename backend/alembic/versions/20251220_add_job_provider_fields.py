"""Add provider tracking to jobs.

Revision ID: 20251220_add_job_provider_fields
Revises: 20251218_add_default_diarizer_provider
Create Date: 2025-12-20 09:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251220_add_job_provider_fields"
down_revision = "20251218_add_default_diarizer_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        # Guardrail: if the core jobs table is missing, recreate it from current metadata.
        # This avoids a hard failure when alembic_version is ahead of the actual schema.
        from app.models.job import Job  # local import to avoid eager app import at module load

        Job.__table__.create(bind, checkfirst=True)
        return
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "asr_provider_used" not in cols:
            batch_op.add_column(sa.Column("asr_provider_used", sa.String(length=50), nullable=True))
        if "diarizer_provider_used" not in cols:
            batch_op.add_column(
                sa.Column("diarizer_provider_used", sa.String(length=50), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'jobs'. Cannot downgrade provider fields.")
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "diarizer_provider_used" in cols:
            batch_op.drop_column("diarizer_provider_used")
        if "asr_provider_used" in cols:
            batch_op.drop_column("asr_provider_used")
