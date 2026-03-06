"""add_notes_table

Revision ID: 2f75271b022a
Revises: 3ebec826ec93
Create Date: 2026-03-04 17:53:15.116600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2f75271b022a'
down_revision: Union[str, None] = '3ebec826ec93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('color', sa.String(length=20), nullable=True),
    sa.Column('position_x', sa.Integer(), nullable=True),
    sa.Column('position_y', sa.Integer(), nullable=True),
    sa.Column('entity_type', sa.String(length=50), nullable=True),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_entity_id'), 'notes', ['entity_id'], unique=False)
    op.create_index(op.f('ix_notes_entity_type'), 'notes', ['entity_type'], unique=False)
    op.create_index(op.f('ix_notes_id'), 'notes', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notes_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_entity_type'), table_name='notes')
    op.drop_index(op.f('ix_notes_entity_id'), table_name='notes')
    op.drop_table('notes')
