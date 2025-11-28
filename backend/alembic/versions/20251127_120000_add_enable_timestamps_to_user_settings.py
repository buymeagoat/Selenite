"""add enable_timestamps to user_settings

Revision ID: add_enable_timestamps_user_settings
Revises: 20251125_0535_4db27c61f220
Create Date: 2025-11-27 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_enable_timestamps_user_settings"
down_revision: Union[str, None] = "20251125_admin_asr_diar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "enable_timestamps",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "enable_timestamps")
