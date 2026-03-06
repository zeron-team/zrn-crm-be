"""add_employees_and_time_entries

Revision ID: 43df0e7b48e8
Revises: faa104d8a0a5
Create Date: 2026-03-05 15:05:45.982678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '43df0e7b48e8'
down_revision: Union[str, None] = 'faa104d8a0a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('employees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('legajo', sa.String(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=False),
    sa.Column('last_name', sa.String(), nullable=False),
    sa.Column('dni', sa.String(), nullable=False),
    sa.Column('cuil', sa.String(), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('marital_status', sa.String(), nullable=True),
    sa.Column('nationality', sa.String(), nullable=True),
    sa.Column('photo_url', sa.String(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('province', sa.String(), nullable=True),
    sa.Column('postal_code', sa.String(), nullable=True),
    sa.Column('hire_date', sa.Date(), nullable=True),
    sa.Column('termination_date', sa.Date(), nullable=True),
    sa.Column('department', sa.String(), nullable=True),
    sa.Column('position', sa.String(), nullable=True),
    sa.Column('supervisor_id', sa.Integer(), nullable=True),
    sa.Column('contract_type', sa.String(), nullable=True),
    sa.Column('billing_type', sa.String(), nullable=True),
    sa.Column('work_schedule', sa.String(), nullable=True),
    sa.Column('weekly_hours', sa.Integer(), nullable=True),
    sa.Column('obra_social', sa.String(), nullable=True),
    sa.Column('obra_social_plan', sa.String(), nullable=True),
    sa.Column('obra_social_number', sa.String(), nullable=True),
    sa.Column('emergency_contact', sa.String(), nullable=True),
    sa.Column('emergency_phone', sa.String(), nullable=True),
    sa.Column('bank_name', sa.String(), nullable=True),
    sa.Column('bank_cbu', sa.String(), nullable=True),
    sa.Column('salary', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('salary_currency', sa.String(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['supervisor_id'], ['employees.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_dni'), 'employees', ['dni'], unique=True)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_legajo'), 'employees', ['legajo'], unique=True)

    op.create_table('time_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_id', sa.Integer(), nullable=False),
    sa.Column('entry_type', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('notes', sa.String(), nullable=True),
    sa.Column('ip_address', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_time_entries_employee_id'), 'time_entries', ['employee_id'], unique=False)
    op.create_index(op.f('ix_time_entries_id'), 'time_entries', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_time_entries_id'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_employee_id'), table_name='time_entries')
    op.drop_table('time_entries')
    op.drop_index(op.f('ix_employees_legajo'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_dni'), table_name='employees')
    op.drop_table('employees')
