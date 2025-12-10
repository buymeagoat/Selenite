"""Ensure model_entries has type column (backfill) for registry stability

Revision ID: 20251207_fix_model_registry_columns
Revises: 20251207_model_registry_sets_entries
Create Date: 2025-12-07 17:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251207_fix_model_registry_columns"
down_revision: Union[str, None] = "20251207_model_registry_sets_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add type column to model_entries if missing (older DBs created manually)
    columns = {col["name"] for col in inspector.get_columns("model_entries")}
    if "type" not in columns:
        op.add_column(
            "model_entries",
            sa.Column("type", sa.String(length=20), nullable=True),
        )
        # Backfill with parent set type when available; otherwise default to 'asr'
        op.execute(
            """
            UPDATE model_entries
            SET type = COALESCE(
                (SELECT model_sets.type FROM model_sets WHERE model_sets.id = model_entries.set_id),
                'asr'
            )
            """
        )
        op.alter_column("model_entries", "type", existing_type=sa.String(length=20), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("model_entries")}
    if "type" in columns:
        op.drop_column("model_entries", "type")
