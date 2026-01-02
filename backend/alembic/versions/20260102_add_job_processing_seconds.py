"""Add processing_seconds accumulator to jobs.

Revision ID: 20260102_add_job_processing_seconds
Revises: 20260102_add_job_pause_fields
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260102_add_job_processing_seconds"
down_revision = "20260102_add_job_pause_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'jobs'. Cannot add processing_seconds.")
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "processing_seconds" not in cols:
            batch_op.add_column(
                sa.Column(
                    "processing_seconds",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "jobs" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'jobs'. Cannot drop processing_seconds.")
    cols = {col["name"] for col in inspector.get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        if "processing_seconds" in cols:
            batch_op.drop_column("processing_seconds")
