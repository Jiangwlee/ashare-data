"""Red window stocks API routes.

Purpose: Provide REST API for querying stocks with X+ red candles in an N-day window.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.repositories import red_window_repository

router = APIRouter(tags=["red-window"])


class RedWindowStockItem(BaseModel):
    """Single red window stock item."""

    code: str = Field(..., description="Stock code (e.g., 600396)")
    name: str = Field(..., description="Stock name")
    sc: str = Field(..., description="Full code (e.g., SH600396)")
    window_days: int = Field(..., description="Observation window size (5 or 7)")
    red_count: int = Field(..., description="Number of red candles in the window")
    rank: int = Field(..., description="Popularity rank")
    gain_pct: float = Field(..., description="Total gain percentage over the window")
    bars: list[dict[str, Any]] = Field(..., description="Daily bars with change_pct")


class RedWindowSummary(BaseModel):
    """Summary of red window stocks for a date."""

    count_5d: int = Field(..., description="Number of 5-day window stocks")
    count_7d: int = Field(..., description="Number of 7-day window stocks")
    total: int = Field(..., description="Total number of stocks")


class RedWindowResponse(BaseModel):
    """Response model for red window stocks query."""

    trade_date: str = Field(..., description="Trading date (YYYY-MM-DD)")
    window_days: int | None = Field(None, description="Window filter applied, if any")
    min_red: int | None = Field(None, description="Minimum red candle filter applied, if any")
    stocks: list[RedWindowStockItem] = Field(..., description="List of matched stocks")
    summary: RedWindowSummary = Field(..., description="Summary statistics")


@router.get("/red-window/daily/{trade_date}", response_model=RedWindowResponse)
def get_red_window_daily(
    trade_date: str,
    days: int | None = Query(default=None, description="Filter by window size: 5 or 7"),
    min_red: int | None = Query(default=None, description="Minimum red candle count"),
) -> RedWindowResponse:
    """Get red window stocks for a specific trading date.

    Returns stocks stored under the configured ingestion criteria:
    - 5-day window: stocks with >=4 red candles
    - 7-day window: stocks with >=6 red candles

    Query params allow further narrowing:
    - days=5: only 5-day window records
    - days=7: only 7-day window records
    - min_red=5: only records where red_count >= 5
    """
    if days is not None and days not in (5, 7):
        raise HTTPException(status_code=400, detail="days must be 5 or 7")

    records = red_window_repository.get_red_window_by_date(trade_date, days, min_red)

    if not records and days is not None:
        raise HTTPException(
            status_code=404,
            detail=f"No red window stocks found for date {trade_date} with days={days}",
        )

    count_5d = 0
    count_7d = 0
    stocks = []

    for record in records:
        if record.window_days == 5:
            count_5d += 1
        elif record.window_days == 7:
            count_7d += 1

        stocks.append(
            RedWindowStockItem(
                code=record.code,
                name=record.name,
                sc=record.sc,
                window_days=record.window_days,
                red_count=record.red_count,
                rank=record.rank,
                gain_pct=record.gain_pct,
                bars=record.bars_json,
            )
        )

    return RedWindowResponse(
        trade_date=trade_date,
        window_days=days,
        min_red=min_red,
        stocks=stocks,
        summary=RedWindowSummary(count_5d=count_5d, count_7d=count_7d, total=len(stocks)),
    )
