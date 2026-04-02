"""THS (同花顺) per-stock fundamental worth page fetcher.

Purpose: Fetch analyst consensus forecasts and historical financials from THS worth page.
DataSource: https://basic.10jqka.com.cn/{code}/worth.html  (public, no auth required)
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

_WORTH_URL = "https://basic.10jqka.com.cn/{code}/worth.html"
_WORTH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://basic.10jqka.com.cn/",
}

_RATING_PATTERNS: list[tuple[str, str]] = [
    ("buy", r"买入\((\d+)\)"),
    ("outperform", r"增持\((\d+)\)"),
    ("neutral", r"中性\((\d+)\)"),
    ("underperform", r"减持\((\d+)\)"),
    ("sell", r"卖出\((\d+)\)"),
]

# Chinese label substring → normalized English key.
# Order matters: longer/more-specific strings must come before shorter prefixes.
_METRIC_LABEL_MAP: list[tuple[str, str]] = [
    ("营业收入增长率", "revenue_growth"),
    ("营业收入", "revenue"),
    ("净利润增长率", "net_profit_growth"),
    ("净利润", "net_profit"),
    ("每股现金流", "cfps"),
    ("每股净资产", "bvps"),
    ("净资产收益率", "roe"),
    ("市盈率", "pe_dynamic"),
]


def _normalize_label(label: str) -> str | None:
    label = label.strip()
    for cn, en in _METRIC_LABEL_MAP:
        if cn in label:
            return en
    return None


def _cell_text(td: Tag) -> str:
    """Extract display value: use <span> text for forecast cells, direct text for actuals."""
    span = td.find("span")
    if span:
        return span.get_text(strip=True)
    return td.get_text(strip=True)


def fetch_worth_data(code: str) -> dict[str, Any]:
    """Fetch analyst consensus and fundamental forecast data for a stock.

    Args:
        code: Stock code, e.g. "603477" or "000001".

    Returns:
        Dict with keys:
          - analyst_count (int): total analysts covering the stock
          - ratings (dict[str, int]): buy/outperform/neutral/underperform/sell counts
          - years (list[str]): column year labels (3 historical + 3 forecast)
          - is_actual (list[bool]): True for historical years
          - metrics (dict[str, list[str]]): per-year string values keyed by metric name
        Returns {} on any failure.
    """
    url = _WORTH_URL.format(code=code)
    try:
        resp = requests.get(url, headers=_WORTH_HEADERS, timeout=15)
        resp.encoding = "gbk"
        html = resp.text
    except Exception as exc:
        logger.exception("fetch_worth_data request failed for %s: %s", code, exc)
        return {}

    try:
        return _parse_worth_html(html)
    except Exception as exc:
        logger.exception("fetch_worth_data parse failed for %s: %s", code, exc)
        return {}


def _parse_worth_html(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    result: dict[str, Any] = {
        "analyst_count": 0,
        "ratings": {},
        "years": [],
        "is_actual": [],
        "metrics": {},
    }

    # --- Analyst ratings ---
    page_text = soup.get_text()
    for key, pattern in _RATING_PATTERNS:
        m = re.search(pattern, page_text)
        result["ratings"][key] = int(m.group(1)) if m else 0
    result["analyst_count"] = sum(result["ratings"].values())

    # --- Metrics table (4th table, 0-indexed = index 3) ---
    # The table has class "organData" and contains nested per-institution sub-tables.
    # Use recursive=False at each level to avoid descending into those sub-tables.
    if len(tables) < 4:
        logger.warning("worth.html: expected >=4 tables, got %d", len(tables))
        return result

    metrics_table = tables[3]

    # Year column labels live in <thead>, not in <tbody>
    thead = metrics_table.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            hcells = header_row.find_all(["th", "td"], recursive=False)
            for hc in hcells[1:]:  # skip "预测指标" label cell
                year_label = hc.get_text(strip=True)
                result["years"].append(year_label)
                result["is_actual"].append("实际" in year_label)

    tbody = metrics_table.find("tbody")
    if not tbody or not result["years"]:
        return result

    num_years = len(result["years"])

    # Each direct row: <th class="tl">label</th> + N <td>value</td> cells
    for row in tbody.find_all("tr", recursive=False):
        label_th = row.find("th", recursive=False)
        cells = row.find_all("td", recursive=False)
        if not label_th or not cells:
            continue
        metric_key = _normalize_label(label_th.get_text(strip=True))
        if not metric_key:
            continue
        values = [_cell_text(c) for c in cells[:num_years]]
        result["metrics"][metric_key] = values

    return result
