"""add_role_configs

Revision ID: 2ad96a31366d
Revises: 43df0e7b48e8
Create Date: 2026-03-05 15:20:31.821392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2ad96a31366d'
down_revision: Union[str, None] = '43df0e7b48e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('role_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('role_name', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('allowed_pages', sa.JSON(), nullable=False),
    sa.Column('own_data_only', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_role_configs_id'), 'role_configs', ['id'], unique=False)
    op.create_index(op.f('ix_role_configs_role_name'), 'role_configs', ['role_name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_role_configs_role_name'), table_name='role_configs')
    op.drop_index(op.f('ix_role_configs_id'), table_name='role_configs')
    op.drop_table('role_configs')
