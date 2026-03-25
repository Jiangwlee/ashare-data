"""New high stocks daily model.

Purpose: Store daily snapshot of stocks that hit new all-time highs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NewHighDaily(Base):
    """Daily record of stocks hitting new all-time highs."""

    __tablename__ = "new_high_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Stock info
    code: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., "600396"
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., "华电辽能"

    # Price data
    price: Mapped[float | None] = mapped_column(Float, nullable=True)  # Current price in CNY
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # Daily change %
    turnover_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Turnover rate %

    # Previous high info
    prev_high: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Previous high price
    prev_high_date: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # Date of previous high

    created_at: Mapped[datetime] = mapped_column(
        String(10), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("trade_date", "code", name="uq_new_high_daily"),
        Index("idx_new_high_code", "code"),
    )
