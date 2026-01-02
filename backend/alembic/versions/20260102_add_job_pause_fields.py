"""Add pause/resume tracking fields to jobs.

Revision ID: 20260102_add_job_pause_fields
Revises: 20251227_add_default_tags_seeded
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260102_add_job_pause_fields"
down_revision = "20251227_add_default_tags_seeded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'jobs'. Cannot add pause fields.")
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "pause_requested_at" not in cols:
            batch_op.add_column(sa.Column("pause_requested_at", sa.DateTime(), nullable=True))
        if "paused_at" not in cols:
            batch_op.add_column(sa.Column("paused_at", sa.DateTime(), nullable=True))
        if "resume_count" not in cols:
            batch_op.add_column(
                sa.Column("resume_count", sa.Integer(), nullable=False, server_default=sa.text("0"))
            )
        if "checkpoint_path" not in cols:
            batch_op.add_column(sa.Column("checkpoint_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'jobs'. Cannot drop pause fields.")
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "checkpoint_path" in cols:
            batch_op.drop_column("checkpoint_path")
        if "resume_count" in cols:
            batch_op.drop_column("resume_count")
        if "paused_at" in cols:
            batch_op.drop_column("paused_at")
        if "pause_requested_at" in cols:
            batch_op.drop_column("pause_requested_at")
