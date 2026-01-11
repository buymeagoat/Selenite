"""Add message inbox fields for feedback submissions.

Revision ID: 20260109_add_message_inbox_fields
Revises: 20260109_add_feedback_submissions
Create Date: 2026-01-09 22:35:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = "20260109_add_message_inbox_fields"
down_revision = "20260109_add_feedback_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "feedback_submissions" not in tables:
        raise RuntimeError("Missing required table 'feedback_submissions'.")

    cols = {col["name"] for col in inspector.get_columns("feedback_submissions")}
    existing_fks = inspector.get_foreign_keys("feedback_submissions")
    fk_columns = {tuple(fk.get("constrained_columns") or []) for fk in existing_fks}
    with op.batch_alter_table("feedback_submissions") as batch_op:
        if "recipient_email" not in cols:
            batch_op.add_column(sa.Column("recipient_email", sa.String(255), nullable=True))
        if "sender_user_id" not in cols:
            batch_op.add_column(sa.Column("sender_user_id", sa.Integer(), nullable=True))
        if "direction" not in cols:
            batch_op.add_column(
                sa.Column(
                    "direction",
                    sa.String(20),
                    nullable=False,
                    server_default=text("'incoming'"),
                )
            )
        if "folder" not in cols:
            batch_op.add_column(
                sa.Column(
                    "folder",
                    sa.String(20),
                    nullable=False,
                    server_default=text("'inbox'"),
                )
            )
        if "is_read" not in cols:
            batch_op.add_column(
                sa.Column(
                    "is_read",
                    sa.Boolean(),
                    nullable=False,
                    server_default=text("0"),
                )
            )
        if "parent_id" not in cols:
            batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        if "thread_id" not in cols:
            batch_op.add_column(sa.Column("thread_id", sa.Integer(), nullable=True))
        if "sent_at" not in cols:
            batch_op.add_column(sa.Column("sent_at", sa.DateTime(), nullable=True))
        if "read_at" not in cols:
            batch_op.add_column(sa.Column("read_at", sa.DateTime(), nullable=True))
        if "deleted_at" not in cols:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        if ("sender_user_id",) not in fk_columns:
            batch_op.create_foreign_key(
                "fk_feedback_submissions_sender_user_id_users",
                "users",
                ["sender_user_id"],
                ["id"],
            )
        if ("parent_id",) not in fk_columns:
            batch_op.create_foreign_key(
                "fk_feedback_submissions_parent_id",
                "feedback_submissions",
                ["parent_id"],
                ["id"],
            )
        if ("thread_id",) not in fk_columns:
            batch_op.create_foreign_key(
                "fk_feedback_submissions_thread_id",
                "feedback_submissions",
                ["thread_id"],
                ["id"],
            )

    if "thread_id" in cols or "thread_id" in {
        col["name"] for col in inspector.get_columns("feedback_submissions")
    }:
        op.execute(text("UPDATE feedback_submissions SET thread_id = id WHERE thread_id IS NULL"))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("feedback_submissions")}
    if "ix_feedback_submissions_folder" not in existing_indexes:
        op.create_index(
            "ix_feedback_submissions_folder",
            "feedback_submissions",
            ["folder"],
            unique=False,
        )
    if "ix_feedback_submissions_thread_id" not in existing_indexes:
        op.create_index(
            "ix_feedback_submissions_thread_id",
            "feedback_submissions",
            ["thread_id"],
            unique=False,
        )
    if "ix_feedback_submissions_parent_id" not in existing_indexes:
        op.create_index(
            "ix_feedback_submissions_parent_id",
            "feedback_submissions",
            ["parent_id"],
            unique=False,
        )
    if "ix_feedback_submissions_is_read" not in existing_indexes:
        op.create_index(
            "ix_feedback_submissions_is_read",
            "feedback_submissions",
            ["is_read"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "feedback_submissions" not in tables:
        raise RuntimeError("Missing required table 'feedback_submissions'.")

    op.drop_index("ix_feedback_submissions_is_read", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_parent_id", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_thread_id", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_folder", table_name="feedback_submissions")

    cols = {col["name"] for col in inspector.get_columns("feedback_submissions")}
    with op.batch_alter_table("feedback_submissions") as batch_op:
        if "deleted_at" in cols:
            batch_op.drop_column("deleted_at")
        if "read_at" in cols:
            batch_op.drop_column("read_at")
        if "sent_at" in cols:
            batch_op.drop_column("sent_at")
        if "thread_id" in cols:
            batch_op.drop_column("thread_id")
        if "parent_id" in cols:
            batch_op.drop_column("parent_id")
        if "is_read" in cols:
            batch_op.drop_column("is_read")
        if "folder" in cols:
            batch_op.drop_column("folder")
        if "direction" in cols:
            batch_op.drop_column("direction")
        if "sender_user_id" in cols:
            batch_op.drop_column("sender_user_id")
        if "recipient_email" in cols:
            batch_op.drop_column("recipient_email")
