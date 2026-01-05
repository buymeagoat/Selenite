"""Add default_asr_provider to user_settings."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251208_add_default_asr_provider"
down_revision = "20251207_fix_model_registry_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_settings", sa.Column("default_asr_provider", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("user_settings", "default_asr_provider")
