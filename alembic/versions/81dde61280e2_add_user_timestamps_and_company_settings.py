"""add_user_timestamps_and_company_settings

Revision ID: 81dde61280e2
Revises: 2ad96a31366d
Create Date: 2026-03-06 23:00:50.534373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '81dde61280e2'
down_revision: Union[str, None] = '2ad96a31366d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timestamp and last_login columns to users table
    op.add_column('users', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
