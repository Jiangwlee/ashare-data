"""Collect full theme-member mappings from THS for all ~362 concepts.

Purpose: Build/refresh the theme_member_stock table by scraping THS concept
member lists.  Designed to run once (or weekly) rather than daily.

Public API:
    collect_theme_members -- main entry point
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

from ashare_data.fetchers.ths_cdp import (
    fetch_concept_ids,
    fetch_concept_members,
)
from app.db.session import open_session
from app.repositories.theme_member_repository import upsert_concept_members

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_PAUSE_AFTER_CONSECUTIVE_FAILURES = 300  # seconds (5 min)
_CONSECUTIVE_FAILURE_THRESHOLD = 3


def _parse_members(raw: dict) -> tuple[list[dict[str, Any]], str]:
    """Extract member list and report_date from raw conceptlist.php response.

    Returns:
        Tuple of (members, report_date) where members is a list of dicts
        with keys: code, name, reason, report_date.
        Returns ([], "") on malformed data.
    """
    try:
        result = raw.get("result", {})
        listdata: dict = result.get("listdata", {})
        if not listdata:
            return [], ""
        report_date = list(listdata.keys())[0]
        raw_members: list = listdata[report_date]
        members = []
        for row in raw_members:
            if not row or not isinstance(row, list) or len(row) < 2:
                continue
            code = str(row[0]).strip()
            name = str(row[1]).strip()
            # Prefer detailed reason [8], fall back to summary [7]
            reason: str | None = None
            if len(row) > 8 and row[8]:
                reason = str(row[8]).strip() or None
            elif len(row) > 7 and row[7]:
                reason = str(row[7]).strip() or None
            members.append(
                {"code": code, "name": name, "reason": reason, "report_date": report_date}
            )
        return members, report_date
    except Exception as exc:
        logger.warning("Failed to parse members from raw response: %s", exc)
        return [], ""


def collect_theme_members(
    *,
    concept_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Scrape THS concept member lists and upsert into theme_member_stock.

    Args:
        concept_ids: Optional list of specific concept IDs to scrape.
                     If None, fetches the full list (~362) from THS.

    Returns:
        Summary dict with keys: total, succeeded, failed, skipped, failed_ids.
    """
    result: dict[str, Any] = {
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "failed_ids": [],
    }

    # Step 1: get concept list
    if concept_ids is None:
        logger.info("Fetching concept ID list from THS gn page...")
        concepts = fetch_concept_ids()
    else:
        concepts = [{"concept_id": cid, "concept_name": ""} for cid in concept_ids]

    result["total"] = len(concepts)
    if not concepts:
        logger.warning("No concept IDs found — aborting")
        return result

    consecutive_failures = 0

    # Step 2: fetch members for each concept
    for idx, concept in enumerate(concepts, start=1):
        cid = concept["concept_id"]
        cname = concept["concept_name"]
        logger.info("[%d/%d] concept %s (%s)", idx, result["total"], cid, cname)

        success = False
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                raw = fetch_concept_members(None, cid)
                if raw.get("errorcode") != 0:
                    logger.warning(
                        "concept %s attempt %d: errorcode=%s msg=%s",
                        cid,
                        attempt,
                        raw.get("errorcode"),
                        raw.get("errormsg"),
                    )
                    time.sleep(2.0)
                    continue

                # Concept name may be missing when user passed explicit ids
                if not cname:
                    cname = raw.get("result", {}).get("name", "")
                    concept["concept_name"] = cname

                members, report_date = _parse_members(raw)
                if not members:
                    logger.warning("concept %s: empty member list — skipping", cid)
                    result["skipped"] += 1
                    success = True
                    break

                with open_session() as db:
                    count = upsert_concept_members(
                        session=db,
                        concept_id=cid,
                        concept_name=cname,
                        members=members,
                    )
                logger.info(
                    "concept %s (%s): saved %d members (report_date=%s)",
                    cid,
                    cname,
                    count,
                    report_date,
                )
                result["succeeded"] += 1
                consecutive_failures = 0
                success = True
                break

            except Exception as exc:
                logger.warning(
                    "concept %s attempt %d error: %s", cid, attempt, exc
                )
                time.sleep(2.0)

        if not success:
            result["failed"] += 1
            result["failed_ids"].append(cid)
            consecutive_failures += 1
            logger.warning("concept %s failed after %d attempts", cid, _MAX_RETRIES)

        if consecutive_failures >= _CONSECUTIVE_FAILURE_THRESHOLD:
            logger.error(
                "%d consecutive failures — pausing %ds before continuing",
                consecutive_failures,
                _PAUSE_AFTER_CONSECUTIVE_FAILURES,
            )
            time.sleep(_PAUSE_AFTER_CONSECUTIVE_FAILURES)
            consecutive_failures = 0

        # Rate limiting: 600–1000 ms between requests
        if idx < result["total"]:
            time.sleep(random.uniform(0.6, 1.0))

    logger.info(
        "collect_theme_members done: total=%d succeeded=%d failed=%d skipped=%d",
        result["total"],
        result["succeeded"],
        result["failed"],
        result["skipped"],
    )
    return result
