"""Add per-user admin default override flags.

Revision ID: 20260112_add_user_default_override_flags
Revises: 20260111_add_signup_password_policy
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260112_add_user_default_override_flags"
down_revision = "20260111_add_signup_password_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_settings" not in inspector.get_table_names():
        from app.models.user_settings import UserSettings  # local import

        UserSettings.__table__.create(bind, checkfirst=True)
        return
    cols = {col["name"] for col in inspector.get_columns("user_settings")}
    with op.batch_alter_table("user_settings") as batch_op:
        if "use_admin_asr_defaults" not in cols:
            batch_op.add_column(
                sa.Column(
                    "use_admin_asr_defaults",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )
        if "use_admin_diarizer_defaults" not in cols:
            batch_op.add_column(
                sa.Column(
                    "use_admin_diarizer_defaults",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )

    # Default both flags to true for existing users so admin defaults apply
    # until a user explicitly overrides their settings.


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_settings" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'user_settings'. Cannot downgrade.")
    cols = {col["name"] for col in inspector.get_columns("user_settings")}
    with op.batch_alter_table("user_settings") as batch_op:
        if "use_admin_diarizer_defaults" in cols:
            batch_op.drop_column("use_admin_diarizer_defaults")
        if "use_admin_asr_defaults" in cols:
            batch_op.drop_column("use_admin_asr_defaults")
