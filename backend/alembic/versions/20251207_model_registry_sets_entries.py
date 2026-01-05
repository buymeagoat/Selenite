"""add model_entries table linked to model_sets

Revision ID: 20251207_model_registry_sets_entries
Revises: 20251206_model_registry
Create Date: 2025-12-07 00:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251207_model_registry_sets_entries"
down_revision: Union[str, None] = "20251206_model_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "model_entries" in inspector.get_table_names():
        return

    op.create_table(
        "model_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "set_id",
            sa.Integer(),
            sa.ForeignKey("model_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=20), nullable=False),  # ASR or DIARIZER (mirrors set)
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("abs_path", sa.String(length=1024), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("disable_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_index("ix_model_entries_set_name", "model_entries", ["set_id", "name"], unique=True)
    op.create_index("ix_model_entries_abs_path", "model_entries", ["abs_path"], unique=True)
    op.create_index("ix_model_entries_set_id", "model_entries", ["set_id"])


def downgrade() -> None:
    op.drop_index("ix_model_entries_set_id", table_name="model_entries")
    op.drop_index("ix_model_entries_abs_path", table_name="model_entries")
    op.drop_index("ix_model_entries_set_name", table_name="model_entries")
    op.drop_table("model_entries")
