"""Add owner_user_id to tags for personal/global separation.

Revision ID: 20260103_add_tag_owner_scope
Revises: 20260102_add_user_admin_audit_log
Create Date: 2026-01-03 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20260103_add_tag_owner_scope"
down_revision: Union[str, None] = "20260102_add_user_admin_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("tags")}
    existing_columns = {col["name"] for col in inspector.get_columns("tags")}

    if "ix_tags_name" in existing_indexes:
        op.drop_index("ix_tags_name", table_name="tags")

    if bind.dialect.name == "sqlite":
        if "owner_user_id" not in existing_columns:
            op.add_column("tags", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    else:
        with op.batch_alter_table("tags") as batch_op:
            if "owner_user_id" not in existing_columns:
                batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tags_owner_user_id_users",
                "users",
                ["owner_user_id"],
                ["id"],
                ondelete="CASCADE",
            )

    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_tags_owner_user_id_users",
            "tags",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if "ix_tags_name" not in existing_indexes:
        op.create_index("ix_tags_name", "tags", ["name"], unique=False)
    if "ix_tags_owner_user_id" not in existing_indexes:
        op.create_index("ix_tags_owner_user_id", "tags", ["owner_user_id"], unique=False)
    if "uq_tags_owner_name" not in existing_indexes:
        op.create_index("uq_tags_owner_name", "tags", ["owner_user_id", "name"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("tags")}

    if "uq_tags_owner_name" in existing_indexes:
        op.drop_index("uq_tags_owner_name", table_name="tags")
    if "ix_tags_owner_user_id" in existing_indexes:
        op.drop_index("ix_tags_owner_user_id", table_name="tags")
    if "ix_tags_name" in existing_indexes:
        op.drop_index("ix_tags_name", table_name="tags")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_tags_owner_user_id_users", "tags", type_="foreignkey")

    if bind.dialect.name == "sqlite":
        op.drop_column("tags", "owner_user_id")
        op.create_index("ix_tags_name", "tags", ["name"], unique=True)
    else:
        with op.batch_alter_table("tags") as batch_op:
            batch_op.create_index("ix_tags_name", ["name"], unique=True)
            batch_op.drop_column("owner_user_id")
