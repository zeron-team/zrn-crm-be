"""add email tables

Revision ID: 7451b23b8005
Revises: 6f72300cf49a
Create Date: 2026-03-04 15:43:59.950803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7451b23b8005'
down_revision: Union[str, None] = '6f72300cf49a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email_address', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=True),
    sa.Column('smtp_host', sa.String(), nullable=False),
    sa.Column('smtp_port', sa.Integer(), nullable=True),
    sa.Column('smtp_user', sa.String(), nullable=False),
    sa.Column('smtp_password', sa.String(), nullable=False),
    sa.Column('smtp_ssl', sa.Boolean(), nullable=True),
    sa.Column('imap_host', sa.String(), nullable=True),
    sa.Column('imap_port', sa.Integer(), nullable=True),
    sa.Column('imap_user', sa.String(), nullable=True),
    sa.Column('imap_password', sa.String(), nullable=True),
    sa.Column('imap_ssl', sa.Boolean(), nullable=True),
    sa.Column('is_default', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_accounts_id'), 'email_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_email_accounts_user_id'), 'email_accounts', ['user_id'], unique=False)

    op.create_table('email_signatures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('html_content', sa.Text(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_signatures_id'), 'email_signatures', ['id'], unique=False)
    op.create_index(op.f('ix_email_signatures_user_id'), 'email_signatures', ['user_id'], unique=False)

    op.create_table('email_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('folder', sa.String(), nullable=True),
    sa.Column('message_id', sa.String(), nullable=True),
    sa.Column('subject', sa.String(), nullable=True),
    sa.Column('from_address', sa.String(), nullable=False),
    sa.Column('to_addresses', sa.Text(), nullable=False),
    sa.Column('cc_addresses', sa.Text(), nullable=True),
    sa.Column('bcc_addresses', sa.Text(), nullable=True),
    sa.Column('body_html', sa.Text(), nullable=True),
    sa.Column('body_text', sa.Text(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('is_starred', sa.Boolean(), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['email_accounts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_messages_folder'), 'email_messages', ['folder'], unique=False)
    op.create_index(op.f('ix_email_messages_id'), 'email_messages', ['id'], unique=False)
    op.create_index(op.f('ix_email_messages_user_id'), 'email_messages', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_messages_user_id'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_id'), table_name='email_messages')
    op.drop_index(op.f('ix_email_messages_folder'), table_name='email_messages')
    op.drop_table('email_messages')
    op.drop_index(op.f('ix_email_signatures_user_id'), table_name='email_signatures')
    op.drop_index(op.f('ix_email_signatures_id'), table_name='email_signatures')
    op.drop_table('email_signatures')
    op.drop_index(op.f('ix_email_accounts_user_id'), table_name='email_accounts')
    op.drop_index(op.f('ix_email_accounts_id'), table_name='email_accounts')
    op.drop_table('email_accounts')
