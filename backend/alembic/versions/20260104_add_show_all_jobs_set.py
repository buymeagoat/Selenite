"""Add show_all_jobs_set to user_settings.

Revision ID: 20260104_add_show_all_jobs_set
Revises: 20260103_add_tag_owner_scope
Create Date: 2026-01-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260104_add_show_all_jobs_set"
down_revision = "20260103_add_tag_owner_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("user_settings")}

    if "show_all_jobs_set" not in existing_columns:
        op.add_column(
            "user_settings",
            sa.Column("show_all_jobs_set", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    dialect_name = op.get_bind().dialect.name
    if "sqlite" not in dialect_name:
        op.alter_column("user_settings", "show_all_jobs_set", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("user_settings")}

    if "show_all_jobs_set" in existing_columns:
        op.drop_column("user_settings", "show_all_jobs_set")
