"""Rename consecutive_red_daily to red_window_daily

Revision ID: 2026_04_01_red_window
Revises: 2026_03_25_add_new_high
Create Date: 2026-04-01 00:00:00.000000

Renames table and updates columns:
  - consecutive_red_daily  ->  red_window_daily
  - consecutive_days       ->  window_days
  - adds red_count (NOT NULL, backfilled from window_days for existing rows)
  - uq_consecutive_red     ->  uq_red_window
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026_04_01_red_window"
down_revision: Union[str, None] = "2026_03_25_add_new_high"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("consecutive_red_daily", "red_window_daily")

    # Rename column consecutive_days -> window_days
    op.alter_column("red_window_daily", "consecutive_days", new_column_name="window_days")

    # Add red_count (nullable first so existing rows can be backfilled)
    op.add_column("red_window_daily", sa.Column("red_count", sa.Integer(), nullable=True))
    # Backfill: existing rows were all-red, so red_count == window_days
    op.execute("UPDATE red_window_daily SET red_count = window_days")
    op.alter_column("red_window_daily", "red_count", nullable=False)

    # Update unique constraint name
    op.drop_constraint("uq_consecutive_red", "red_window_daily", type_="unique")
    op.create_unique_constraint("uq_red_window", "red_window_daily", ["trade_date", "sc", "window_days"])

    # Update index names
    op.drop_index("ix_consecutive_red_daily_trade_date", table_name="red_window_daily")
    op.drop_index("ix_consecutive_red_daily_run_id", table_name="red_window_daily")
    op.drop_index("ix_consecutive_red_daily_consecutive_days", table_name="red_window_daily")
    op.create_index("ix_red_window_daily_trade_date", "red_window_daily", ["trade_date"])
    op.create_index("ix_red_window_daily_run_id", "red_window_daily", ["run_id"])
    op.create_index("ix_red_window_daily_window_days", "red_window_daily", ["window_days"])


def downgrade() -> None:
    op.drop_index("ix_red_window_daily_window_days", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_run_id", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_trade_date", table_name="red_window_daily")

    op.drop_constraint("uq_red_window", "red_window_daily", type_="unique")
    op.create_unique_constraint(
        "uq_consecutive_red", "red_window_daily", ["trade_date", "sc", "window_days"]
    )

    op.drop_column("red_window_daily", "red_count")
    op.alter_column("red_window_daily", "window_days", new_column_name="consecutive_days")

    op.create_index("ix_consecutive_red_daily_consecutive_days", "red_window_daily", ["consecutive_days"])
    op.create_index("ix_consecutive_red_daily_run_id", "red_window_daily", ["run_id"])
    op.create_index("ix_consecutive_red_daily_trade_date", "red_window_daily", ["trade_date"])

    op.rename_table("red_window_daily", "consecutive_red_daily")
