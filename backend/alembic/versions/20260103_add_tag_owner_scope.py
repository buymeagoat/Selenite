"""Add owner_user_id to tags for personal/global separation.

Revision ID: 20260103_add_tag_owner_scope
Revises: 20260102_add_user_admin_audit_log
Create Date: 2026-01-03 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260103_add_tag_owner_scope"
down_revision: Union[str, None] = "20260102_add_user_admin_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tags") as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch_op.drop_index("ix_tags_name")
        batch_op.create_index("ix_tags_name", ["name"], unique=False)
        batch_op.create_index("ix_tags_owner_user_id", ["owner_user_id"], unique=False)
        batch_op.create_unique_constraint("uq_tags_owner_name", ["owner_user_id", "name"])
        batch_op.create_foreign_key(
            "fk_tags_owner_user_id_users",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch_op:
        batch_op.drop_constraint("fk_tags_owner_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("uq_tags_owner_name", type_="unique")
        batch_op.drop_index("ix_tags_owner_user_id")
        batch_op.drop_index("ix_tags_name")
        batch_op.create_index("ix_tags_name", ["name"], unique=True)
        batch_op.drop_column("owner_user_id")
