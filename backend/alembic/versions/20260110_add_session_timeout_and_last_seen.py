"""Add session timeout settings and user last_seen_at.

Revision ID: 20260110_add_session_timeout_and_last_seen
Revises: 20260109_add_message_inbox_fields
Create Date: 2026-01-10 00:10:00.000000
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = "20260110_add_session_timeout_and_last_seen"
down_revision = "20260109_add_message_inbox_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "system_preferences" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'system_preferences'.")
    if "users" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'users'.")

    prefs_cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "session_timeout_minutes" not in prefs_cols:
            batch_op.add_column(
                sa.Column("session_timeout_minutes", sa.Integer(), nullable=False, server_default=text("30"))
            )
        if "auth_token_not_before" not in prefs_cols:
            batch_op.add_column(sa.Column("auth_token_not_before", sa.DateTime(), nullable=True))

    users_cols = {col["name"] for col in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "last_seen_at" not in users_cols:
            batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))

    op.execute(
        text(
            "UPDATE system_preferences SET session_timeout_minutes = 30 "
            "WHERE session_timeout_minutes IS NULL"
        )
    )
    op.execute(
        text(
            "UPDATE system_preferences SET auth_token_not_before = :now "
            "WHERE auth_token_not_before IS NULL"
        ).bindparams(now=datetime.utcnow())
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "system_preferences" in inspector.get_table_names():
        prefs_cols = {col["name"] for col in inspector.get_columns("system_preferences")}
        with op.batch_alter_table("system_preferences") as batch_op:
            if "auth_token_not_before" in prefs_cols:
                batch_op.drop_column("auth_token_not_before")
            if "session_timeout_minutes" in prefs_cols:
                batch_op.drop_column("session_timeout_minutes")

    if "users" in inspector.get_table_names():
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        with op.batch_alter_table("users") as batch_op:
            if "last_seen_at" in user_cols:
                batch_op.drop_column("last_seen_at")
