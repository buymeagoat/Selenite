"""Add feedback submissions and delivery settings.

Revision ID: 20260109_add_feedback_submissions
Revises: 20260104_add_show_all_jobs_set
Create Date: 2026-01-09 19:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260109_add_feedback_submissions"
down_revision = "20260104_add_show_all_jobs_set"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "feedback_submissions" not in tables:
        op.create_table(
            "feedback_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category", sa.String(length=50), nullable=False, server_default="comment"),
            sa.Column("subject", sa.String(length=200), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("submitter_name", sa.String(length=200), nullable=True),
            sa.Column("submitter_email", sa.String(length=255), nullable=True),
            sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("email_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("webhook_status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("delivery_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index(
            "ix_feedback_submissions_created_at",
            "feedback_submissions",
            ["created_at"],
            unique=False,
        )
        op.create_index(
            "ix_feedback_submissions_user_id",
            "feedback_submissions",
            ["user_id"],
            unique=False,
        )

    if "feedback_attachments" not in tables:
        op.create_table(
            "feedback_attachments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=120), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("storage_path", sa.String(length=512), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["submission_id"],
                ["feedback_submissions.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_feedback_attachments_submission_id",
            "feedback_attachments",
            ["submission_id"],
            unique=False,
        )

    if "system_preferences" not in tables:
        from app.models.system_preferences import SystemPreferences

        SystemPreferences.__table__.create(bind, checkfirst=True)
        return

    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "feedback_store_enabled" not in cols:
            batch_op.add_column(
                sa.Column(
                    "feedback_store_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )
        if "feedback_email_enabled" not in cols:
            batch_op.add_column(
                sa.Column(
                    "feedback_email_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "feedback_webhook_enabled" not in cols:
            batch_op.add_column(
                sa.Column(
                    "feedback_webhook_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "feedback_destination_email" not in cols:
            batch_op.add_column(sa.Column("feedback_destination_email", sa.String(255), nullable=True))
        if "feedback_webhook_url" not in cols:
            batch_op.add_column(sa.Column("feedback_webhook_url", sa.String(512), nullable=True))
        if "smtp_host" not in cols:
            batch_op.add_column(sa.Column("smtp_host", sa.String(255), nullable=True))
        if "smtp_port" not in cols:
            batch_op.add_column(sa.Column("smtp_port", sa.Integer(), nullable=True))
        if "smtp_username" not in cols:
            batch_op.add_column(sa.Column("smtp_username", sa.String(255), nullable=True))
        if "smtp_password" not in cols:
            batch_op.add_column(sa.Column("smtp_password", sa.String(255), nullable=True))
        if "smtp_from_email" not in cols:
            batch_op.add_column(sa.Column("smtp_from_email", sa.String(255), nullable=True))
        if "smtp_use_tls" not in cols:
            batch_op.add_column(
                sa.Column(
                    "smtp_use_tls",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "feedback_attachments" in tables:
        op.drop_index("ix_feedback_attachments_submission_id", table_name="feedback_attachments")
        op.drop_table("feedback_attachments")

    if "feedback_submissions" in tables:
        op.drop_index("ix_feedback_submissions_user_id", table_name="feedback_submissions")
        op.drop_index("ix_feedback_submissions_created_at", table_name="feedback_submissions")
        op.drop_table("feedback_submissions")

    if "system_preferences" not in tables:
        raise RuntimeError(
            "Missing required table 'system_preferences'. Cannot downgrade feedback settings."
        )

    cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "smtp_use_tls" in cols:
            batch_op.drop_column("smtp_use_tls")
        if "smtp_from_email" in cols:
            batch_op.drop_column("smtp_from_email")
        if "smtp_password" in cols:
            batch_op.drop_column("smtp_password")
        if "smtp_username" in cols:
            batch_op.drop_column("smtp_username")
        if "smtp_port" in cols:
            batch_op.drop_column("smtp_port")
        if "smtp_host" in cols:
            batch_op.drop_column("smtp_host")
        if "feedback_webhook_url" in cols:
            batch_op.drop_column("feedback_webhook_url")
        if "feedback_destination_email" in cols:
            batch_op.drop_column("feedback_destination_email")
        if "feedback_webhook_enabled" in cols:
            batch_op.drop_column("feedback_webhook_enabled")
        if "feedback_email_enabled" in cols:
            batch_op.drop_column("feedback_email_enabled")
        if "feedback_store_enabled" in cols:
            batch_op.drop_column("feedback_store_enabled")
