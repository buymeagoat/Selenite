"""Add user admin fields, audit logs, and per-user show_all_jobs.

Revision ID: 20260102_add_user_admin_audit_log
Revises: 20260102_add_job_processing_seconds
Create Date: 2026-01-02 12:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260102_add_user_admin_audit_log"
down_revision = "20260102_add_job_processing_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = inspector.get_table_names()

    if "users" not in table_names:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "force_password_reset",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
        op.create_index("ix_users_email", "users", ["email"], unique=False)
        user_cols = {
            "id",
            "username",
            "email",
            "hashed_password",
            "created_at",
            "updated_at",
            "is_admin",
            "is_disabled",
            "force_password_reset",
            "last_login_at",
        }
    else:
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        with op.batch_alter_table("users") as batch_op:
            if "is_admin" not in user_cols:
                batch_op.add_column(
                    sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0"))
                )
            if "is_disabled" not in user_cols:
                batch_op.add_column(
                    sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.text("0"))
                )
            if "force_password_reset" not in user_cols:
                batch_op.add_column(
                    sa.Column(
                        "force_password_reset",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )
            if "last_login_at" not in user_cols:
                batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
            # Normalize username length for email-based login.
            batch_op.alter_column("username", type_=sa.String(255))

        existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_email" not in existing_indexes:
            op.create_index("ix_users_email", "users", ["email"], unique=False)

    if "jobs" not in table_names:
        raise RuntimeError("Missing required table 'jobs'. Cannot adjust user ownership.")
    job_cols = {col["name"] for col in inspector.get_columns("jobs")}
    if "user_id" in job_cols:
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.alter_column("user_id", nullable=True)

    if "user_settings" not in table_names:
        raise RuntimeError("Missing required table 'user_settings'. Cannot add show_all_jobs.")
    settings_cols = {col["name"] for col in inspector.get_columns("user_settings")}
    if "show_all_jobs" not in settings_cols:
        with op.batch_alter_table("user_settings") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "show_all_jobs", sa.Boolean(), nullable=False, server_default=sa.text("0")
                )
            )

    if "audit_logs" not in table_names:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("target_type", sa.String(length=100), nullable=True),
            sa.Column("target_id", sa.String(length=100), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False
        )
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = inspector.get_table_names()

    if "audit_logs" in table_names:
        op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
        op.drop_index("ix_audit_logs_action", table_name="audit_logs")
        op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
        op.drop_table("audit_logs")

    if "user_settings" not in table_names:
        raise RuntimeError("Missing required table 'user_settings'. Cannot drop show_all_jobs.")
    settings_cols = {col["name"] for col in inspector.get_columns("user_settings")}
    if "show_all_jobs" in settings_cols:
        with op.batch_alter_table("user_settings") as batch_op:
            batch_op.drop_column("show_all_jobs")

    if "jobs" not in table_names:
        raise RuntimeError("Missing required table 'jobs'. Cannot restore user ownership.")
    job_cols = {col["name"] for col in inspector.get_columns("jobs")}
    if "user_id" in job_cols:
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.alter_column("user_id", nullable=False)

    if "users" not in table_names:
        raise RuntimeError("Missing required table 'users'. Cannot drop admin fields.")
    user_cols = {col["name"] for col in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "last_login_at" in user_cols:
            batch_op.drop_column("last_login_at")
        if "force_password_reset" in user_cols:
            batch_op.drop_column("force_password_reset")
        if "is_disabled" in user_cols:
            batch_op.drop_column("is_disabled")
        if "is_admin" in user_cols:
            batch_op.drop_column("is_admin")
        batch_op.alter_column("username", type_=sa.String(50))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    if "ix_users_email" in existing_indexes:
        op.drop_index("ix_users_email", table_name="users")
