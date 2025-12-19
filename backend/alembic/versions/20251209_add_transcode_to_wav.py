"""Add transcode_to_wav flag to system_preferences

Revision ID: 20251209_add_transcode_to_wav
Revises: 20251209_add_time_zones
Create Date: 2025-12-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251209_add_transcode_to_wav"
down_revision = "20251209_add_time_zones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("system_preferences")]
    if "transcode_to_wav" not in cols:
        op.add_column(
            "system_preferences",
            sa.Column("transcode_to_wav", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        # remove server_default after applying (SQLite doesn't support ALTER COLUMN DROP DEFAULT)
        if not is_sqlite:
            op.alter_column("system_preferences", "transcode_to_wav", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("system_preferences")]
    if "transcode_to_wav" in cols:
        op.drop_column("system_preferences", "transcode_to_wav")
