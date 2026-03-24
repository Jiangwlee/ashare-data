"""Consecutive red stocks repository.

Purpose: Database operations for ConsecutiveRedDaily model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.session import open_session
from app.models.consecutive_red_daily import ConsecutiveRedDaily


def save_consecutive_red_stocks(
    trade_date: str,
    run_id: str,
    consecutive_days: int,
    matches: list[dict[str, Any]],
) -> int:
    """Save consecutive red stocks to database.

    Args:
        trade_date: Trading date in format YYYY-MM-DD
        run_id: Run identifier
        consecutive_days: Number of consecutive days (5 or 7)
        matches: List of matched stocks from build_red_for_n_days

    Returns:
        Number of records saved
    """
    with open_session() as session:
        # Delete existing records for this date and consecutive_days
        session.query(ConsecutiveRedDaily).filter_by(
            trade_date=trade_date,
            consecutive_days=consecutive_days,
        ).delete()

        # Insert new records
        count = 0
        for match in matches:
            # Convert bars to simplified format with change_pct only
            bars_simplified = []
            bars = match.get("bars", [])
            for i, bar in enumerate(bars):
                change_pct = 0.0
                if i > 0 and bars[i - 1]["open"] > 0:
                    change_pct = round(
                        (bar["close"] - bars[i - 1]["close"])
                        / bars[i - 1]["close"]
                        * 100,
                        2,
                    )
                bars_simplified.append(
                    {
                        "date": bar["date"],
                        "change_pct": change_pct,
                    }
                )

            record = ConsecutiveRedDaily(
                trade_date=trade_date,
                run_id=run_id,
                code=match["code"],
                name=match["name"],
                sc=match["sc"],
                consecutive_days=consecutive_days,
                rank=match["rank"],
                gain_pct=match["gain_n_days_pct"],
                bars_json=bars_simplified,
                created_at=datetime.utcnow(),
            )
            session.add(record)
            count += 1

        session.commit()
        return count


def get_consecutive_red_by_date(
    trade_date: str,
    consecutive_days: int | None = None,
) -> list[ConsecutiveRedDaily]:
    """Get consecutive red stocks for a specific date.

    Args:
        trade_date: Trading date in format YYYY-MM-DD
        consecutive_days: Filter by specific days (5 or 7), or None for all

    Returns:
        List of ConsecutiveRedDaily records
    """
    with open_session() as session:
        query = (
            session.query(ConsecutiveRedDaily)
            .filter_by(trade_date=trade_date)
            .order_by(
                ConsecutiveRedDaily.consecutive_days.desc(),
                ConsecutiveRedDaily.rank.asc(),
            )
        )

        if consecutive_days is not None:
            query = query.filter_by(consecutive_days=consecutive_days)

        return query.all()


def delete_old_records(retention_days: int = 30) -> int:
    """Delete records older than retention_days.

    Args:
        retention_days: Number of days to retain

    Returns:
        Number of records deleted
    """
    from datetime import timedelta

    cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).date()

    with open_session() as session:
        result = (
            session.query(ConsecutiveRedDaily)
            .filter(ConsecutiveRedDaily.trade_date < cutoff_date)
            .delete()
        )
        session.commit()
        return result
