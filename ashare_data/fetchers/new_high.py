"""New high stocks fetcher from THS (同花顺) data center.

Purpose: Fetch stocks that hit new all-time highs from 10jqka.com.cn.
DataSource: https://data.10jqka.com.cn/rank/cxg/
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# API URL for history high stocks (board=1 means 历史新高)
_THS_NEW_HIGH_URL = "https://data.10jqka.com.cn/rank/cxg/board/1/field/stockcode/order/desc/ajax/1/free/1/"
_THS_HEADERS = {
    "Referer": "https://data.10jqka.com.cn/rank/cxg/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Cookie can be set via environment variable ASHARE_THS_COOKIE
# Format: "key1=value1; key2=value2"
_THS_COOKIE = os.environ.get("ASHARE_THS_COOKIE", "")


@dataclass
class NewHighStock:
    """A stock that hit new all-time high."""

    code: str  # e.g., "600396"
    name: str  # e.g., "华电辽能"
    change_pct: float | None = None  # e.g., 10.02 (percent)
    turnover_rate: float | None = None  # e.g., 16.07 (percent)
    price: float | None = None  # current price in CNY
    prev_high: float | None = None  # previous high price
    prev_high_date: str | None = None  # e.g., "2026-03-23"


def fetch_new_high_stocks() -> list[NewHighStock]:
    """Fetch stocks that hit new all-time highs.

    Returns:
        List of NewHighStock objects, empty list on error.

    Raises:
        RuntimeError: If HTTP request fails after retries.
    """
    try:
        html = _fetch_html()
    except Exception as exc:
        logger.error("fetch_new_high_stocks HTTP request failed: %s", exc)
        raise RuntimeError(f"Failed to fetch new high stocks: {exc}") from exc

    return _parse_html(html)


def _fetch_html() -> str:
    """Fetch HTML from THS API with proper headers and cookies."""
    session = requests.Session()
    session.headers.update(_THS_HEADERS)
    
    if _THS_COOKIE:
        # Parse cookie string into dict
        cookies = {}
        for pair in _THS_COOKIE.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key.strip()] = value.strip()
        session.cookies.update(cookies)
    
    # First visit the main page to establish session
    try:
        session.get("https://data.10jqka.com.cn/rank/cxg/", timeout=10)
    except requests.RequestException as e:
        logger.warning("Failed to visit main page: %s", e)
    
    # Then fetch the API
    response = session.get(_THS_NEW_HIGH_URL, timeout=15)
    response.raise_for_status()
    return response.text


def _parse_html(html: str) -> list[NewHighStock]:
    """Parse HTML table and extract stock data.

    Args:
        html: Raw HTML response from THS API.

    Returns:
        List of NewHighStock objects.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        logger.warning("No table found in response")
        return []

    rows = table.find_all("tr")
    stocks: list[NewHighStock] = []

    # Skip header row (index 0), process data rows
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 8:
            continue

        try:
            stock = _parse_row(cells)
            if stock:
                stocks.append(stock)
        except Exception as e:
            logger.warning("Failed to parse row: %s", e)
            continue

    logger.info("Parsed %d new high stocks", len(stocks))
    return stocks


def _parse_row(cells: list[Any]) -> NewHighStock | None:
    """Parse a single table row into NewHighStock.

    Column order (0-indexed):
    0: 序号 (index)
    1: 股票代码 (code)
    2: 股票简称 (name)
    3: 涨跌幅 (change_pct, e.g., "7.99%")
    4: 换手率 (turnover_rate, e.g., "6.28%")
    5: 最新价 (price, e.g., "20.00")
    6: 前期高点 (prev_high, e.g., "19.68")
    7: 前期高点日期 (prev_high_date, e.g., "2026-01-20")
    """
    code = cells[1].get_text(strip=True)
    name = cells[2].get_text(strip=True)

    # Parse percentage fields (e.g., "7.99%" → 7.99)
    change_pct = _parse_percent(cells[3].get_text(strip=True))
    turnover_rate = _parse_percent(cells[4].get_text(strip=True))

    # Parse price fields
    price = _parse_float(cells[5].get_text(strip=True))
    prev_high = _parse_float(cells[6].get_text(strip=True))
    prev_high_date = cells[7].get_text(strip=True)

    return NewHighStock(
        code=code,
        name=name,
        change_pct=change_pct,
        turnover_rate=turnover_rate,
        price=price,
        prev_high=prev_high,
        prev_high_date=prev_high_date,
    )


def _parse_percent(value: str) -> float | None:
    """Parse percentage string to float.

    Args:
        value: e.g., "7.99%" or ""

    Returns:
        Float value or None if parsing fails.
    """
    if not value:
        return None
    try:
        return float(value.rstrip("%"))
    except (ValueError, AttributeError):
        return None


def _parse_float(value: str) -> float | None:
    """Parse string to float.

    Args:
        value: e.g., "20.00" or ""

    Returns:
        Float value or None if parsing fails.
    """
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, AttributeError):
        return None


__all__ = ["NewHighStock", "fetch_new_high_stocks"]
