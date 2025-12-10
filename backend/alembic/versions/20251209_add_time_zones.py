"""Add user and server time zone support."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251209_add_time_zones"
down_revision = "20251208_add_default_asr_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("time_zone", sa.String(length=100), nullable=True))
    op.create_table(
        "system_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_time_zone", sa.String(length=100), nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    # Ensure a single preferences row exists
    op.execute("INSERT INTO system_preferences (id, server_time_zone) VALUES (1, 'UTC')")


def downgrade() -> None:
    op.drop_table("system_preferences")
    op.drop_column("user_settings", "time_zone")
