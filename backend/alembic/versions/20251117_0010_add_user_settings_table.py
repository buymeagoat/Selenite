"""add user_settings table

Revision ID: 20251117_add_user_settings
Revises: 8e56132aa15d
Create Date: 2025-11-17 00:10:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251117_add_user_settings'
down_revision: Union[str, None] = '8e56132aa15d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('default_model', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('default_language', sa.String(length=10), nullable=False, server_default='auto'),
        sa.Column('max_concurrent_jobs', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', name='uq_user_settings_user'),
    )


def downgrade() -> None:
    op.drop_table('user_settings')
