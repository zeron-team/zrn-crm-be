"""add_seller_id_to_purchase_orders

Revision ID: faa104d8a0a5
Revises: 2f75271b022a
Create Date: 2026-03-04 23:29:22.424856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'faa104d8a0a5'
down_revision: Union[str, None] = '2f75271b022a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_orders', sa.Column('seller_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_purchase_orders_seller_id', 'purchase_orders', 'users', ['seller_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_purchase_orders_seller_id', 'purchase_orders', type_='foreignkey')
    op.drop_column('purchase_orders', 'seller_id')
