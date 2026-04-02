"""Tonghuashun site adapters backed by the reusable CDP collector."""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from ashare_data.cdp import CdpClient, CdpPageSession

logger = logging.getLogger(__name__)

_THS_QUOTE_CENTER_URL = "https://q.10jqka.com.cn/"
_THS_DATA_CENTER_URL = "https://data.10jqka.com.cn/rank/cxg/"
_THS_CONCEPT_LIST_URL = "https://q.10jqka.com.cn/gn/"
_THS_CONCEPT_AUTH_URL = "https://basic.10jqka.com.cn/000001/concept.html"
_THS_CONCEPT_MEMBERS_API = "https://basic.10jqka.com.cn/ajax/stock/conceptlist.php"


def fetch_indexflash_via_cdp() -> dict:
    """Fetch THS indexflash payload via a real browser session."""
    client = CdpClient()
    session = client.open_page(_THS_QUOTE_CENTER_URL)
    try:
        session.wait_for_network_idle(1.5)
        return session.fetch_json("/api.php?t=indexflash", headers={"Accept": "*/*"})
    finally:
        session.close()


_GN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_concept_ids(session: CdpPageSession | None = None) -> list[dict[str, str]]:
    """Fetch all THS concept IDs and names from the gn listing page.

    Uses a plain HTTP GET (no auth required). The session parameter is accepted
    but unused — it is kept for backwards compatibility with the pipeline.

    Returns:
        List of dicts with keys: concept_id, concept_name.
        Deduped and ordered as they appear on the page.
    """
    resp = requests.get(_THS_CONCEPT_LIST_URL, headers=_GN_HEADERS, timeout=15)
    resp.encoding = "gbk"
    soup = BeautifulSoup(resp.text, "html.parser")
    seen: set[str] = set()
    concepts: list[dict[str, str]] = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/gn/detail/code/" not in href:
            continue
        m = re.search(r"/gn/detail/code/(\d+)/", href)
        if not m:
            continue
        concept_id = m.group(1)
        if concept_id in seen:
            continue
        name = link.get_text(strip=True)
        if name:
            seen.add(concept_id)
            concepts.append({"concept_id": concept_id, "concept_name": name})
    logger.info("Found %d concept IDs from THS gn page", len(concepts))
    return concepts


_MEMBERS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": _THS_CONCEPT_AUTH_URL,
}


def fetch_concept_members(session: CdpPageSession | None, concept_id: str) -> dict:
    """Fetch all member stocks for a THS concept.

    Uses a plain HTTP GET — no auth cookie required. The session parameter is
    accepted but unused, kept for backwards compatibility with the pipeline.

    Args:
        session: Unused (kept for API compatibility).
        concept_id: THS concept ID string, e.g. "309264".

    Returns:
        Raw API response dict with keys errorcode, errormsg, result.
        Caller must check errorcode == 0 before consuming result.
    """
    url = f"{_THS_CONCEPT_MEMBERS_API}?cid={concept_id}&code=000001"
    resp = requests.get(url, headers=_MEMBERS_HEADERS, timeout=30)
    return resp.json()


def fetch_new_high_html_via_cdp(board: str = "1") -> str:
    """Fetch new high stocks HTML from THS data center via CDP.

    Args:
        board: Board type, "1" for all-time high, "2" for 60-day high, etc.

    Returns:
        HTML string containing the stock table.

    Raises:
        CdpUnavailableError: If CDP is not available.
        CdpFetchError: If fetch fails.
    """
    client = CdpClient()
    session = client.open_page(_THS_DATA_CENTER_URL)
    try:
        session.wait_for_network_idle(2.0)
        # The API endpoint path
        api_path = f"/rank/cxg/board/{board}/field/stockcode/order/desc/ajax/1/free/1/"
        html = session.fetch_text(api_path)
        logger.info("Fetched new high stocks (board=%s) via CDP", board)
        return html
    finally:
        session.close()
