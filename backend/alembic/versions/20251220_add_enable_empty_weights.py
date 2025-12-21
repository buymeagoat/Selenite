"""Add enable_empty_weights to system_preferences.

Revision ID: 20251220_add_enable_empty_weights
Revises: 20251220_add_job_provider_fields
Create Date: 2025-12-20 15:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251220_add_enable_empty_weights"
down_revision = "20251220_add_job_provider_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_preferences" not in inspector.get_table_names():
        # Guardrail: recreate missing system_preferences table from current metadata.
        from app.models.system_preferences import SystemPreferences

        SystemPreferences.__table__.create(bind, checkfirst=True)
        return
    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "enable_empty_weights" not in cols:
            batch_op.add_column(
                sa.Column("enable_empty_weights", sa.Boolean(), nullable=False, server_default=sa.text("0"))
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_preferences" not in inspector.get_table_names():
        raise RuntimeError(
            "Missing required table 'system_preferences'. Cannot downgrade enable_empty_weights."
        )
    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "enable_empty_weights" in cols:
            batch_op.drop_column("enable_empty_weights")
