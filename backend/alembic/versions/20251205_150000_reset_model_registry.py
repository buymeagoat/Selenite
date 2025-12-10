"""placeholder to bridge missing reset_model_registry revision

Revision ID: 20251205_150000_reset_model_registry
Revises: add_enable_timestamps_user_settings
Create Date: 2025-12-05 15:00:00
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401  (kept for symmetry; no-ops here)

# revision identifiers, used by Alembic.
revision: str = "20251205_150000_reset_model_registry"
down_revision: Union[str, None] = "add_enable_timestamps_user_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op placeholder to bridge historical reset revision that was never committed.
    # Leaving this empty keeps alembic history linear for existing databases.
    pass


def downgrade() -> None:
    # No-op downgrade; nothing was created in this placeholder.
    pass
