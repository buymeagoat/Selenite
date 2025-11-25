"""add speaker detection fields

Revision ID: 4db27c61f220
Revises: 20251122_progress_fields
Create Date: 2025-11-25 05:35:31.092768

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4db27c61f220'
down_revision: Union[str, None] = '20251122_progress_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("jobs")}
    if "speaker_count" not in cols:
        op.add_column("jobs", sa.Column("speaker_count", sa.Integer(), nullable=True))
    # Note: has_speaker_labels already exists; this adds the requested count hint.


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("jobs")}
    if "speaker_count" in cols:
        op.drop_column("jobs", "speaker_count")
