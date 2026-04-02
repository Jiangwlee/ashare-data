"""Add theme_member_stock table

Revision ID: 2026_04_02_theme_member
Revises: 2026_04_01_red_window
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_02_theme_member'
down_revision: Union[str, None] = '2026_04_01_red_window'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'theme_member_stock',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.String(16), nullable=False),
        sa.Column('concept_name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('report_date', sa.String(10), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('concept_id', 'code', name='uq_theme_member'),
    )
    op.create_index('ix_theme_member_concept_id', 'theme_member_stock', ['concept_id'])
    op.create_index('ix_theme_member_code', 'theme_member_stock', ['code'])


def downgrade() -> None:
    op.drop_index('ix_theme_member_code', table_name='theme_member_stock')
    op.drop_index('ix_theme_member_concept_id', table_name='theme_member_stock')
    op.drop_table('theme_member_stock')
