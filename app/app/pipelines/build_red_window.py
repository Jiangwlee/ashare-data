"""Build red window stocks data.

Purpose: Scan for 5-day (>=4 red) and 7-day (>=6 red) candle patterns and save to DB.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.runtime import today_cn
from app.pipelines.red_for_n_days import build_red_for_n_days
from app.repositories import red_window_repository

logger = logging.getLogger(__name__)

# Ingestion criteria: (window_days, min_red, min_gain_pct)
_SCAN_CONFIGS: list[tuple[int, int, float]] = [(5, 4, 10.0), (7, 6, 10.0)]


def build_red_window(
    trade_date: str | None = None,
    run_id: str | None = None,
    top_n: int = 2000,
) -> dict[str, Any]:
    """Build red window stocks for configured (window_days, min_red) combinations.

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
        run_id = build_run_id(trade_date, "red-window")

    logger.info(
        "Building red window data for %s (run_id: %s, top_n: %d)",
        trade_date,
        run_id,
        top_n,
    )

    results: dict[str, Any] = {
        "run_id": run_id,
        "trade_date": trade_date,
        "top_n": top_n,
    }

    for window_days, min_red, min_gain_pct in _SCAN_CONFIGS:
        key = f"days_{window_days}_min_{min_red}"
        try:
            logger.info("Scanning %d-day window, min_red=%d, min_gain=%.1f%%...", window_days, min_red, min_gain_pct)
            scan_result = build_red_for_n_days(
                trade_date=trade_date,
                days=window_days,
                min_red=min_red,
                min_gain_pct=min_gain_pct,
                top_n=top_n,
            )
            count = red_window_repository.save_red_window_stocks(
                trade_date=trade_date,
                run_id=run_id,
                window_days=window_days,
                matches=scan_result["matches"],
            )
            results[key] = {"count": count, "error": None}
            logger.info("Saved %d records for %d-day / min_red=%d", count, window_days, min_red)
        except Exception as e:
            logger.exception("Failed to build %d-day red window: %s", window_days, e)
            results[key] = {"count": 0, "error": str(e)}

    try:
        deleted = red_window_repository.delete_old_records(retention_days=30)
        logger.info("Deleted %d old red window records", deleted)
        results["cleanup_deleted"] = deleted
    except Exception as e:
        logger.warning("Failed to cleanup old records: %s", e)

    return results
