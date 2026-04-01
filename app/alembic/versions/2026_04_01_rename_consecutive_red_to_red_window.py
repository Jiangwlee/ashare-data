"""Rename consecutive_red_daily to red_window_daily

Revision ID: 2026_04_01_red_window
Revises: 2026_03_25_add_new_high
Create Date: 2026-04-01 00:00:00.000000

SQLite does not support ALTER COLUMN, so we use create-copy-drop strategy:
  - Create red_window_daily with updated schema
  - Copy data from consecutive_red_daily (consecutive_days -> window_days,
    red_count backfilled as window_days since all existing rows were all-red)
  - Drop consecutive_red_daily
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026_04_01_red_window"
down_revision: Union[str, None] = "2026_03_25_add_new_high"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "red_window_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.String(10), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("sc", sa.String(16), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("red_count", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("gain_pct", sa.Float(), nullable=False),
        sa.Column("bars_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "sc", "window_days", name="uq_red_window"),
    )
    op.create_index("ix_red_window_daily_trade_date", "red_window_daily", ["trade_date"])
    op.create_index("ix_red_window_daily_run_id", "red_window_daily", ["run_id"])
    op.create_index("ix_red_window_daily_window_days", "red_window_daily", ["window_days"])

    # Copy existing data; existing rows were all-red so red_count = consecutive_days
    op.execute("""
        INSERT INTO red_window_daily
            (id, trade_date, run_id, code, name, sc,
             window_days, red_count, rank, gain_pct, bars_json, created_at)
        SELECT
            id, trade_date, run_id, code, name, sc,
            consecutive_days, consecutive_days, rank, gain_pct, bars_json, created_at
        FROM consecutive_red_daily
    """)

    op.drop_index("ix_consecutive_red_daily_consecutive_days", table_name="consecutive_red_daily")
    op.drop_index("ix_consecutive_red_daily_run_id", table_name="consecutive_red_daily")
    op.drop_index("ix_consecutive_red_daily_trade_date", table_name="consecutive_red_daily")
    op.drop_table("consecutive_red_daily")


def downgrade() -> None:
    op.create_table(
        "consecutive_red_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trade_date", sa.String(10), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("sc", sa.String(16), nullable=False),
        sa.Column("consecutive_days", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("gain_pct", sa.Float(), nullable=False),
        sa.Column("bars_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "sc", "consecutive_days", name="uq_consecutive_red"),
    )
    op.create_index("ix_consecutive_red_daily_trade_date", "consecutive_red_daily", ["trade_date"])
    op.create_index("ix_consecutive_red_daily_run_id", "consecutive_red_daily", ["run_id"])
    op.create_index("ix_consecutive_red_daily_consecutive_days", "consecutive_red_daily", ["consecutive_days"])

    op.execute("""
        INSERT INTO consecutive_red_daily
            (id, trade_date, run_id, code, name, sc,
             consecutive_days, rank, gain_pct, bars_json, created_at)
        SELECT
            id, trade_date, run_id, code, name, sc,
            window_days, rank, gain_pct, bars_json, created_at
        FROM red_window_daily
    """)

    op.drop_index("ix_red_window_daily_window_days", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_run_id", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_trade_date", table_name="red_window_daily")
    op.drop_table("red_window_daily")
