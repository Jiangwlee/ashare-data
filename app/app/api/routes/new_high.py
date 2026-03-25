"""API routes for new high stocks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.session import open_session
from app.models.new_high_daily import NewHighDaily
from app.repositories.new_high_repository import (
    delete_old_records,
    get_by_date,
    get_stock_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["new-high"])


@router.get("/daily/{trade_date}")
def get_new_high_daily(trade_date: str) -> dict[str, Any]:
    """Get new high stocks for a specific trading date.

    Args:
        trade_date: Trading date in YYYY-MM-DD format

    Returns:
        Dictionary containing trade_date and list of stocks
    """
    try:
        datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    with open_session() as session:
        stocks = get_by_date(session=session, trade_date=trade_date)

    return {
        "trade_date": trade_date,
        "count": len(stocks),
        "stocks": [
            {
                "code": s.code,
                "name": s.name,
                "price": s.price,
                "change_pct": s.change_pct,
                "turnover_rate": s.turnover_rate,
                "prev_high": s.prev_high,
                "prev_high_date": s.prev_high_date,
            }
            for s in stocks
        ],
    }


@router.get("/stocks/{code}")
def get_new_high_history(code: str) -> dict[str, Any]:
    """Get new high history for a specific stock.

    Args:
        code: Stock code (e.g., "600396")

    Returns:
        Dictionary containing code and list of historical records
    """
    with open_session() as session:
        records = get_stock_history(session=session, code=code)

    return {
        "code": code,
        "count": len(records),
        "history": [
            {
                "trade_date": s.trade_date,
                "name": s.name,
                "price": s.price,
                "change_pct": s.change_pct,
                "prev_high": s.prev_high,
                "prev_high_date": s.prev_high_date,
            }
            for s in records
        ],
    }


@router.get("/stats/breakthrough")
def get_breakthrough_stats(days: int = 30) -> dict[str, Any]:
    """Get statistics of stocks hitting new high in recent days.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        Dictionary containing breakthrough statistics
    """
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

    cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    with open_session() as session:
        # Get all records in the period
        records = (
            session.query(NewHighDaily)
            .filter(NewHighDaily.trade_date >= cutoff_date)
            .all()
        )

    if not records:
        return {
            "days": days,
            "cutoff_date": cutoff_date,
            "total_records": 0,
            "unique_stocks": 0,
            "stocks": [],
        }

    # Count occurrences per stock
    stock_counts: dict[str, int] = {}
    for r in records:
        stock_counts[r.code] = stock_counts.get(r.code, 0) + 1

    # Sort by count desc
    sorted_stocks = sorted(stock_counts.items(), key=lambda x: (-x[1], x[0]))

    return {
        "days": days,
        "cutoff_date": cutoff_date,
        "total_records": len(records),
        "unique_stocks": len(stock_counts),
        "stocks": [
            {"code": code, "breakthrough_count": count} for code, count in sorted_stocks
        ],
    }
