"""Add new_high_daily table

Revision ID: 2026_03_25_add_new_high
Revises: 2026_03_24_add_consecutive_red
Create Date: 2026-03-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_03_25_add_new_high'
down_revision: Union[str, None] = '2026_03_24_add_consecutive_red'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'new_high_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_date', sa.String(10), nullable=False),
        sa.Column('run_id', sa.String(64), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('change_pct', sa.Float(), nullable=True),
        sa.Column('turnover_rate', sa.Float(), nullable=True),
        sa.Column('prev_high', sa.Float(), nullable=True),
        sa.Column('prev_high_date', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'code', name='uq_new_high_daily')
    )
    op.create_index('ix_new_high_daily_trade_date', 'new_high_daily', ['trade_date'])
    op.create_index('ix_new_high_daily_run_id', 'new_high_daily', ['run_id'])
    op.create_index('idx_new_high_code', 'new_high_daily', ['code'])


def downgrade() -> None:
    op.drop_index('idx_new_high_code', table_name='new_high_daily')
    op.drop_index('ix_new_high_daily_run_id', table_name='new_high_daily')
    op.drop_index('ix_new_high_daily_trade_date', table_name='new_high_daily')
    op.drop_table('new_high_daily')
