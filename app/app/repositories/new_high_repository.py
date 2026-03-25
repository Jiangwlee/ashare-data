"""Repository for new high daily data."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.new_high_daily import NewHighDaily

logger = logging.getLogger(__name__)


def save_new_high_stocks(
    *,
    session: Session,
    trade_date: str,
    run_id: str,
    stocks: list[dict[str, Any]],
) -> int:
    """Save new high stocks to database.

    Args:
        session: Database session
        trade_date: Trading date (YYYY-MM-DD)
        run_id: Run identifier
        stocks: List of stock data dicts with keys: code, name, price, change_pct, etc.

    Returns:
        Number of records inserted
    """
    if not stocks:
        logger.info("No new high stocks to save for %s", trade_date)
        return 0

    # Delete existing records for this date (idempotent)
    deleted = session.query(NewHighDaily).filter(
        NewHighDaily.trade_date == trade_date
    ).delete()
    if deleted > 0:
        logger.info("Deleted %d existing records for %s", deleted, trade_date)

    # Prepare bulk insert data
    insert_data = []
    for stock in stocks:
        insert_data.append(
            {
                "trade_date": trade_date,
                "run_id": run_id,
                "code": stock.get("code", ""),
                "name": stock.get("name", ""),
                "price": stock.get("price"),
                "change_pct": stock.get("change_pct"),
                "turnover_rate": stock.get("turnover_rate"),
                "prev_high": stock.get("prev_high"),
                "prev_high_date": stock.get("prev_high_date"),
            }
        )

    # Bulk insert
    session.bulk_insert_mappings(NewHighDaily, insert_data)
    session.commit()

    logger.info("Saved %d new high stocks for %s", len(insert_data), trade_date)
    return len(insert_data)


def get_by_date(*, session: Session, trade_date: str) -> list[NewHighDaily]:
    """Get new high stocks for a specific date.

    Args:
        session: Database session
        trade_date: Trading date (YYYY-MM-DD)

    Returns:
        List of NewHighDaily records
    """
    return (
        session.query(NewHighDaily)
        .filter(NewHighDaily.trade_date == trade_date)
        .order_by(NewHighDaily.change_pct.desc())
        .all()
    )


def get_stock_history(*, session: Session, code: str) -> list[NewHighDaily]:
    """Get new high history for a specific stock.

    Args:
        session: Database session
        code: Stock code

    Returns:
        List of NewHighDaily records ordered by date desc
    """
    return (
        session.query(NewHighDaily)
        .filter(NewHighDaily.code == code)
        .order_by(NewHighDaily.trade_date.desc())
        .all()
    )


def delete_old_records(*, session: Session, retention_days: int = 30) -> int:
    """Delete old records beyond retention period.

    Args:
        session: Database session
        retention_days: Number of days to retain

    Returns:
        Number of deleted records
    """
    from datetime import datetime, timedelta

    cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    deleted = session.query(NewHighDaily).filter(
        NewHighDaily.trade_date < cutoff_date
    ).delete()
    session.commit()
    logger.info("Deleted %d new_high records older than %s", deleted, cutoff_date)
    return deleted
