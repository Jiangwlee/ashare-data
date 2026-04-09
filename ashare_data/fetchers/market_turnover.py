"""Market turnover fetcher from THS market analysis charts.

Purpose: Fetch market-wide daily turnover for THS all-A universe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ashare_data.core.http_client import http_json

logger = logging.getLogger(__name__)
_CST = timezone(timedelta(hours=8))

_THS_TURNOVER_URL = (
    "https://dq.10jqka.com.cn/fuyao/market_analysis_api/chart/v1/get_chart_data?chart_key=turnover_day"
)
_THS_HEADERS = {
    "Referer": "https://www.10jqka.com.cn/",
}


@dataclass
class MarketTurnover:
    """Market turnover snapshot."""

    trade_date: str | None = None
    market_volume: float | None = None
    source_name: str = "同花顺全A(沪深京)"
    source_code: str = "883957"


def fetch_market_turnover_for_date(trade_date: str) -> MarketTurnover:
    """Fetch THS all-A daily turnover for one trade date.

    Args:
        trade_date: Trade date in YYYYMMDD format.

    Returns:
        MarketTurnover with market_volume in yi yuan.
    """
    try:
        resp = http_json(url=_THS_TURNOVER_URL, headers=_THS_HEADERS, timeout=10, retries=1)
    except Exception as exc:
        logger.warning("fetch_market_turnover_for_date 请求失败: %s", exc)
        return MarketTurnover(trade_date=trade_date)

    charts = ((resp.get("data") or {}).get("charts") or {})
    points = charts.get("point_list") or []
    target_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"

    for point in points:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            point_date = datetime.fromtimestamp(point[0] / 1000, tz=_CST).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            continue
        if point_date != target_date:
            continue
        try:
            market_volume = round(float(point[1]) / 100000000, 2)
        except (TypeError, ValueError):
            market_volume = None
        return MarketTurnover(trade_date=trade_date, market_volume=market_volume)
    return MarketTurnover(trade_date=trade_date)
