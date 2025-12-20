"""Add provider tracking to jobs.

Revision ID: 20251220_add_job_provider_fields
Revises: 20251218_add_default_diarizer_provider
Create Date: 2025-12-20 09:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251220_add_job_provider_fields"
down_revision = "20251218_add_default_diarizer_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("asr_provider_used", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("diarizer_provider_used", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("diarizer_provider_used")
        batch_op.drop_column("asr_provider_used")
