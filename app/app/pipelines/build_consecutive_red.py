"""Build consecutive red stocks data.

Purpose: Scan for 5-day and 7-day consecutive positive candles and save to DB.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.runtime import today_cn
from app.pipelines.red_for_n_days import build_red_for_n_days
from app.repositories import consecutive_red_repository

logger = logging.getLogger(__name__)


def build_consecutive_red(
    trade_date: str | None = None,
    run_id: str | None = None,
    top_n: int = 2000,
) -> dict[str, Any]:
    """Build consecutive red stocks for 5-day and 7-day.

    Args:
        trade_date: Trading date (YYYY-MM-DD), defaults to today
        run_id: Run identifier, auto-generated if not provided
        top_n: Number of top popularity stocks to scan

    Returns:
        Summary of results including counts and any errors
    """
    if trade_date is None:
        trade_date = today_cn()

    if run_id is None:
        from app.core.runtime import build_run_id

        run_id = build_run_id(trade_date, "consecutive-red")

    logger.info(
        "Building consecutive red data for %s (run_id: %s, top_n: %d)",
        trade_date,
        run_id,
        top_n,
    )

    results = {
        "run_id": run_id,
        "trade_date": trade_date,
        "top_n": top_n,
        "days_5": {"count": 0, "error": None},
        "days_7": {"count": 0, "error": None},
    }

    # Scan 5-day consecutive red
    try:
        logger.info("Scanning for 5-day consecutive red...")
        result_5d = build_red_for_n_days(
            trade_date=trade_date,
            days=5,
            top_n=top_n,
        )
        count_5d = consecutive_red_repository.save_consecutive_red_stocks(
            trade_date=trade_date,
            run_id=run_id,
            consecutive_days=5,
            matches=result_5d["matches"],
        )
        results["days_5"]["count"] = count_5d
        logger.info("Saved %d 5-day consecutive red stocks", count_5d)
    except Exception as e:
        logger.exception("Failed to build 5-day consecutive red: %s", e)
        results["days_5"]["error"] = str(e)

    # Scan 7-day consecutive red
    try:
        logger.info("Scanning for 7-day consecutive red...")
        result_7d = build_red_for_n_days(
            trade_date=trade_date,
            days=7,
            top_n=top_n,
        )
        count_7d = consecutive_red_repository.save_consecutive_red_stocks(
            trade_date=trade_date,
            run_id=run_id,
            consecutive_days=7,
            matches=result_7d["matches"],
        )
        results["days_7"]["count"] = count_7d
        logger.info("Saved %d 7-day consecutive red stocks", count_7d)
    except Exception as e:
        logger.exception("Failed to build 7-day consecutive red: %s", e)
        results["days_7"]["error"] = str(e)

    # Cleanup old records (retention: 30 days)
    try:
        deleted = consecutive_red_repository.delete_old_records(retention_days=30)
        logger.info("Deleted %d old consecutive red records", deleted)
        results["cleanup_deleted"] = deleted
    except Exception as e:
        logger.warning("Failed to cleanup old records: %s", e)

    return results
