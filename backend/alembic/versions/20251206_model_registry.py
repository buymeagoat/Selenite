"""create model_sets table for admin-managed registry

Revision ID: 20251206_model_registry
Revises: 20251205_150000_reset_model_registry
Create Date: 2025-12-06 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251206_model_registry"
down_revision: Union[str, None] = "20251205_150000_reset_model_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Some environments already created model_sets during a prior reset; skip recreation to keep upgrades idempotent.
    if "model_sets" in inspector.get_table_names():
        return

    op.create_table(
        "model_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=20), nullable=False),  # ASR or DIARIZER
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("abs_path", sa.String(length=1024), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("disable_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_index("ix_model_sets_type_name", "model_sets", ["type", "name"], unique=True)
    op.create_index("ix_model_sets_abs_path", "model_sets", ["abs_path"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_model_sets_abs_path", table_name="model_sets")
    op.drop_index("ix_model_sets_type_name", table_name="model_sets")
    op.drop_table("model_sets")
