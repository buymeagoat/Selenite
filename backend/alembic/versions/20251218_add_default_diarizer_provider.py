"""Add default_diarizer_provider column

Revision ID: 20251218_add_default_diarizer_provider
Revises: 20251216_fix_models_root_path
Create Date: 2025-12-18 07:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251218_add_default_diarizer_provider"
down_revision: Union[str, None] = "20251216_fix_models_root_path"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("default_diarizer_provider", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "default_diarizer_provider")
