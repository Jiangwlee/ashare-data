"""Red window stocks repository.

Purpose: Database operations for RedWindowDaily model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.session import open_session
from app.models.red_window_daily import RedWindowDaily


def save_red_window_stocks(
    trade_date: str,
    run_id: str,
    window_days: int,
    matches: list[dict[str, Any]],
) -> int:
    """Save red window stocks to database.

    Args:
        trade_date: Trading date in format YYYY-MM-DD
        run_id: Run identifier
        window_days: Observation window size (5 or 7)
        matches: List of matched stocks from build_red_for_n_days

    Returns:
        Number of records saved
    """
    with open_session() as session:
        session.query(RedWindowDaily).filter_by(
            trade_date=trade_date,
            window_days=window_days,
        ).delete()

        count = 0
        for match in matches:
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

            record = RedWindowDaily(
                trade_date=trade_date,
                run_id=run_id,
                code=match["code"],
                name=match["name"],
                sc=match["sc"],
                window_days=window_days,
                red_count=match["red_count"],
                rank=match["rank"],
                gain_pct=match["gain_n_days_pct"],
                bars_json=bars_simplified,
                created_at=datetime.utcnow(),
            )
            session.add(record)
            count += 1

        session.commit()
        return count


def get_red_window_by_date(
    trade_date: str,
    window_days: int | None = None,
    min_red: int | None = None,
) -> list[RedWindowDaily]:
    """Get red window stocks for a specific date.

    Args:
        trade_date: Trading date in format YYYY-MM-DD
        window_days: Filter by observation window (5 or 7), or None for all
        min_red: Minimum red candle count filter, or None for all

    Returns:
        List of RedWindowDaily records
    """
    with open_session() as session:
        query = (
            session.query(RedWindowDaily)
            .filter_by(trade_date=trade_date)
            .order_by(
                RedWindowDaily.window_days.desc(),
                RedWindowDaily.rank.asc(),
            )
        )

        if window_days is not None:
            query = query.filter(RedWindowDaily.window_days == window_days)

        if min_red is not None:
            query = query.filter(RedWindowDaily.red_count >= min_red)

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
            session.query(RedWindowDaily)
            .filter(RedWindowDaily.trade_date < cutoff_date)
            .delete()
        )
        session.commit()
        return result
