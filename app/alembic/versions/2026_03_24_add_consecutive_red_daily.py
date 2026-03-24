"""Add consecutive_red_daily table

Revision ID: 2026_03_24_add_consecutive_red
Revises: 
Create Date: 2026-03-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_03_24_add_consecutive_red'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'consecutive_red_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('run_id', sa.String(64), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('sc', sa.String(16), nullable=False),
        sa.Column('consecutive_days', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('gain_pct', sa.Float(), nullable=False),
        sa.Column('bars_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sc', 'consecutive_days', name='uq_consecutive_red')
    )
    op.create_index('ix_consecutive_red_daily_trade_date', 'consecutive_red_daily', ['trade_date'])
    op.create_index('ix_consecutive_red_daily_run_id', 'consecutive_red_daily', ['run_id'])
    op.create_index('ix_consecutive_red_daily_consecutive_days', 'consecutive_red_daily', ['consecutive_days'])


def downgrade() -> None:
    op.drop_index('ix_consecutive_red_daily_consecutive_days', table_name='consecutive_red_daily')
    op.drop_index('ix_consecutive_red_daily_run_id', table_name='consecutive_red_daily')
    op.drop_index('ix_consecutive_red_daily_trade_date', table_name='consecutive_red_daily')
    op.drop_table('consecutive_red_daily')
