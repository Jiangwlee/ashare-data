"""Build new high stocks data.

Purpose: Fetch and save daily new all-time high stocks from THS.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.runtime import today_cn
from app.db.session import open_session
from app.repositories.new_high_repository import delete_old_records, save_new_high_stocks
from ashare_data.fetchers.new_high import fetch_new_high_stocks

logger = logging.getLogger(__name__)


def build_new_high(
    trade_date: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build new high stocks data for one trading day.

    Args:
        trade_date: Trading date (YYYY-MM-DD), defaults to today
        run_id: Run identifier, auto-generated if not provided

    Returns:
        Summary of results including counts and any errors
    """
    if trade_date is None:
        trade_date = today_cn()

    if run_id is None:
        from app.core.runtime import build_run_id

        run_id = build_run_id(trade_date, "new-high")

    logger.info(
        "Building new high data for %s (run_id: %s)",
        trade_date,
        run_id,
    )

    result = {
        "run_id": run_id,
        "trade_date": trade_date,
        "count": 0,
        "error": None,
    }

    try:
        # Fetch data from THS
        logger.info("Fetching new high stocks from THS...")
        stocks = fetch_new_high_stocks()
        logger.info("Fetched %d new high stocks", len(stocks))

        # Convert to dict list for repository
        stock_dicts = [
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
        ]

        # Save to database
        with open_session() as session:
            count = save_new_high_stocks(
                session=session,
                trade_date=trade_date,
                run_id=run_id,
                stocks=stock_dicts,
            )
            result["count"] = count

        logger.info("Successfully saved %d new high stocks", count)

    except Exception as e:
        logger.exception("Failed to build new high data: %s", e)
        result["error"] = str(e)

    # Cleanup old records (retention: 30 days)
    try:
        with open_session() as session:
            deleted = delete_old_records(session=session, retention_days=30)
            logger.info("Deleted %d old new_high records", deleted)
            result["cleanup_deleted"] = deleted
    except Exception as e:
        logger.warning("Failed to cleanup old records: %s", e)

    return result
