"""Add last-selected registry set fields to user_settings."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251214_last_selected_registry_sets"
down_revision = "20251210_seed_curated_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("last_selected_asr_set", sa.String(length=255), nullable=True))
    op.add_column("user_settings", sa.Column("last_selected_diarizer_set", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "last_selected_diarizer_set")
    op.drop_column("user_settings", "last_selected_asr_set")
