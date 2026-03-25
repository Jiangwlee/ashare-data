"""Tonghuashun site adapters backed by the reusable CDP collector."""

from __future__ import annotations

import logging

from ashare_data.cdp import CdpClient

logger = logging.getLogger(__name__)

_THS_QUOTE_CENTER_URL = "https://q.10jqka.com.cn/"
_THS_DATA_CENTER_URL = "https://data.10jqka.com.cn/rank/cxg/"


def fetch_indexflash_via_cdp() -> dict:
    """Fetch THS indexflash payload via a real browser session."""
    client = CdpClient()
    session = client.open_page(_THS_QUOTE_CENTER_URL)
    try:
        session.wait_for_network_idle(1.5)
        return session.fetch_json("/api.php?t=indexflash", headers={"Accept": "*/*"})
    finally:
        session.close()


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
