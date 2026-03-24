"""Consecutive red stocks API routes.

Purpose: Provide REST API for querying consecutive red stocks (5-day and 7-day).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any

from app.repositories import consecutive_red_repository

router = APIRouter(tags=["consecutive-red"])


class ConsecutiveRedStockItem(BaseModel):
    """Single consecutive red stock item."""
    code: str = Field(..., description="Stock code (e.g., 600396)")
    name: str = Field(..., description="Stock name")
    sc: str = Field(..., description="Full code (e.g., SH600396)")
    consecutive_days: int = Field(..., description="5 or 7 days")
    rank: int = Field(..., description="Popularity rank")
    gain_pct: float = Field(..., description="Total gain percentage over N days")
    bars: list[dict[str, Any]] = Field(..., description="Daily change percentages")


class ConsecutiveRedSummary(BaseModel):
    """Summary of consecutive red stocks for a date."""
    count_5d: int = Field(..., description="Number of 5-day consecutive red stocks")
    count_7d: int = Field(..., description="Number of 7-day consecutive red stocks")
    total: int = Field(..., description="Total number of stocks")


class ConsecutiveRedResponse(BaseModel):
    """Response model for consecutive red stocks query."""
    trade_date: str = Field(..., description="Trading date (YYYY-MM-DD)")
    consecutive_days: int | None = Field(None, description="Filter by specific days if provided")
    stocks: list[ConsecutiveRedStockItem] = Field(..., description="List of consecutive red stocks")
    summary: ConsecutiveRedSummary = Field(..., description="Summary statistics")


@router.get("/consecutive-red/daily/{trade_date}", response_model=ConsecutiveRedResponse)
def get_consecutive_red_daily(
    trade_date: str,
    days: int | None = Query(default=None, description="Filter by specific days: 5 or 7"),
) -> ConsecutiveRedResponse:
    """Get consecutive red stocks for a specific trading date.
    
    Returns stocks with 5-day and/or 7-day consecutive positive candles
    (close >= open) from the specified trading date.
    
    - days=5: Return only 5-day consecutive red stocks
    - days=7: Return only 7-day consecutive red stocks
    - days not specified: Return both 5-day and 7-day stocks
    """
    # Validate days parameter
    if days is not None and days not in (5, 7):
        raise HTTPException(
            status_code=400,
            detail="Invalid days parameter. Must be 5 or 7."
        )
    
    # Query database
    records = consecutive_red_repository.get_consecutive_red_by_date(trade_date, days)
    
    if not records and days is not None:
        raise HTTPException(
            status_code=404,
            detail=f"No {days}-day consecutive red stocks found for date {trade_date}"
        )
    
    # Convert to response model
    stocks = []
    count_5d = 0
    count_7d = 0
    
    for record in records:
        if record.consecutive_days == 5:
            count_5d += 1
        elif record.consecutive_days == 7:
            count_7d += 1
        
        stocks.append(ConsecutiveRedStockItem(
            code=record.code,
            name=record.name,
            sc=record.sc,
            consecutive_days=record.consecutive_days,
            rank=record.rank,
            gain_pct=record.gain_pct,
            bars=record.bars_json,
        ))
    
    return ConsecutiveRedResponse(
        trade_date=trade_date,
        consecutive_days=days,
        stocks=stocks,
        summary=ConsecutiveRedSummary(
            count_5d=count_5d,
            count_7d=count_7d,
            total=len(stocks),
        ),
    )
