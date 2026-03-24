"""Consecutive red daily model.

Purpose: Store stocks with consecutive positive candles (5-day and 7-day).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConsecutiveRedDaily(Base):
    """Daily record of stocks with consecutive positive candles."""

    __tablename__ = "consecutive_red_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Stock info
    code: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., 600396
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., 华电辽能
    sc: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., SH600396

    # Metrics
    consecutive_days: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # 5 or 7
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # Popularity rank
    gain_pct: Mapped[float] = mapped_column(Float, nullable=False)  # Total gain %

    # Simplified K-line: list of {date: str, change_pct: float}
    bars_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "sc", "consecutive_days", name="uq_consecutive_red"
        ),
    )
