"""Red window daily model.

Purpose: Store stocks with X or more red candles in an N-day window.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RedWindowDaily(Base):
    """Daily record of stocks with >= min_red candles in an N-day window."""

    __tablename__ = "red_window_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Stock info
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sc: Mapped[str] = mapped_column(String(16), nullable=False)

    # Metrics
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # N (5 or 7)
    red_count: Mapped[int] = mapped_column(Integer, nullable=False)                # X red candles
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    gain_pct: Mapped[float] = mapped_column(Float, nullable=False)

    bars_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("trade_date", "sc", "window_days", name="uq_red_window"),
    )
