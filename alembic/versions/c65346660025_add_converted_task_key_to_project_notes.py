"""add_converted_task_key_to_project_notes

Revision ID: c65346660025
Revises: 02a072b19ede
Create Date: 2026-03-12 13:51:11.479081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c65346660025'
down_revision: Union[str, None] = '02a072b19ede'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_notes', sa.Column('converted_task_key', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('project_notes', 'converted_task_key')
