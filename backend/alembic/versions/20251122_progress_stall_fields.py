"""add progress/stall tracking columns to jobs

Revision ID: 20251122_progress_fields
Revises: 20251117_add_user_settings
Create Date: 2025-11-22 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251122_progress_fields"
down_revision: Union[str, None] = "20251117_add_user_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {col["name"] for col in insp.get_columns("jobs")}

    if "updated_at" not in cols:
        op.add_column(
            "jobs",
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        # Backfill updated_at with created_at for existing rows then drop server_default where supported
        op.execute("UPDATE jobs SET updated_at = COALESCE(updated_at, created_at)")
        if bind.dialect.name != "sqlite":
            op.alter_column("jobs", "updated_at", server_default=None)
    if "estimated_total_seconds" not in cols:
        op.add_column("jobs", sa.Column("estimated_total_seconds", sa.Integer(), nullable=True))
    if "stalled_at" not in cols:
        op.add_column("jobs", sa.Column("stalled_at", sa.DateTime(), nullable=True))

    # Ensure index exists (create_if_not_exists not available across all backends)
    indexes = {ix["name"] for ix in insp.get_indexes("jobs")}
    if "ix_jobs_updated_at" not in indexes and "updated_at" in cols.union({"updated_at"}):
        op.create_index(op.f("ix_jobs_updated_at"), "jobs", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_updated_at"), table_name="jobs")
    op.drop_column("jobs", "stalled_at")
    op.drop_column("jobs", "estimated_total_seconds")
    op.drop_column("jobs", "updated_at")
