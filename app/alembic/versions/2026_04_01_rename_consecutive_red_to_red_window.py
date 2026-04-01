"""Rename consecutive_red_daily to red_window_daily

Revision ID: 2026_04_01_red_window
Revises: 2026_03_25_add_new_high
Create Date: 2026-04-01 00:00:00.000000

Handles two entry states:
  A) Fresh: consecutive_red_daily exists  -> create new table, copy, drop old
  B) Partial: red_window_daily already exists with NULLs -> fix up remaining state
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "2026_04_01_red_window"
down_revision: Union[str, None] = "2026_03_25_add_new_high"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def _index_exists(conn, table: str, index_name: str) -> bool:
    return any(i["name"] == index_name for i in inspect(conn).get_indexes(table))


def _constraint_exists(conn, table: str, constraint_name: str) -> bool:
    return any(
        u["name"] == constraint_name
        for u in inspect(conn).get_unique_constraints(table)
    )


def upgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "consecutive_red_daily"):
        # State A: fresh install — create new table, copy data, drop old
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
        conn.execute(text("""
            INSERT INTO red_window_daily
                (id, trade_date, run_id, code, name, sc,
                 window_days, red_count, rank, gain_pct, bars_json, created_at)
            SELECT
                id, trade_date, run_id, code, name, sc,
                consecutive_days, consecutive_days, rank, gain_pct, bars_json, created_at
            FROM consecutive_red_daily
        """))
        op.drop_index("ix_consecutive_red_daily_consecutive_days", table_name="consecutive_red_daily")
        op.drop_index("ix_consecutive_red_daily_run_id", table_name="consecutive_red_daily")
        op.drop_index("ix_consecutive_red_daily_trade_date", table_name="consecutive_red_daily")
        op.drop_table("consecutive_red_daily")
    else:
        # State B: red_window_daily already exists (partial previous run) — fix up
        conn.execute(text(
            "UPDATE red_window_daily SET red_count = window_days WHERE red_count IS NULL"
        ))

    # Fix indexes (may be old-named or missing)
    for old_idx in (
        "ix_consecutive_red_daily_trade_date",
        "ix_consecutive_red_daily_run_id",
        "ix_consecutive_red_daily_consecutive_days",
    ):
        if _index_exists(conn, "red_window_daily", old_idx):
            op.drop_index(old_idx, table_name="red_window_daily")

    if not _index_exists(conn, "red_window_daily", "ix_red_window_daily_trade_date"):
        op.create_index("ix_red_window_daily_trade_date", "red_window_daily", ["trade_date"])
    if not _index_exists(conn, "red_window_daily", "ix_red_window_daily_run_id"):
        op.create_index("ix_red_window_daily_run_id", "red_window_daily", ["run_id"])
    if not _index_exists(conn, "red_window_daily", "ix_red_window_daily_window_days"):
        op.create_index("ix_red_window_daily_window_days", "red_window_daily", ["window_days"])

    # Fix unique constraint name
    if _constraint_exists(conn, "red_window_daily", "uq_consecutive_red"):
        op.drop_constraint("uq_consecutive_red", "red_window_daily", type_="unique")
    if not _constraint_exists(conn, "red_window_daily", "uq_red_window"):
        op.create_unique_constraint("uq_red_window", "red_window_daily", ["trade_date", "sc", "window_days"])


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

    conn = op.get_bind()
    conn.execute(text("""
        INSERT INTO consecutive_red_daily
            (id, trade_date, run_id, code, name, sc,
             consecutive_days, rank, gain_pct, bars_json, created_at)
        SELECT
            id, trade_date, run_id, code, name, sc,
            window_days, rank, gain_pct, bars_json, created_at
        FROM red_window_daily
    """))

    op.drop_index("ix_red_window_daily_window_days", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_run_id", table_name="red_window_daily")
    op.drop_index("ix_red_window_daily_trade_date", table_name="red_window_daily")
    op.drop_table("red_window_daily")
