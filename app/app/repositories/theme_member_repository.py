"""Repository for theme_member_stock data."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.theme_member_stock import ThemeMemberStock

logger = logging.getLogger(__name__)


def upsert_concept_members(
    *,
    session: Session,
    concept_id: str,
    concept_name: str,
    members: list[dict[str, Any]],
) -> int:
    """Replace all member rows for a concept and insert fresh data.

    Deletes existing rows for concept_id then bulk-inserts new ones.

    Args:
        session: Database session.
        concept_id: THS concept ID string, e.g. "309264".
        concept_name: Human-readable concept name.
        members: Parsed member list; each dict must have keys:
                 code, name, reason (optional), report_date.

    Returns:
        Number of rows inserted.
    """
    if not members:
        logger.info("No members to save for concept %s (%s)", concept_id, concept_name)
        return 0

    session.query(ThemeMemberStock).filter(
        ThemeMemberStock.concept_id == concept_id
    ).delete()

    now = datetime.utcnow()
    rows = [
        {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "code": m["code"],
            "name": m["name"],
            "reason": m.get("reason"),
            "report_date": m["report_date"],
            "updated_at": now,
        }
        for m in members
    ]
    session.bulk_insert_mappings(ThemeMemberStock, rows)
    session.commit()
    return len(rows)


def get_concepts_for_stock(*, session: Session, code: str) -> list[ThemeMemberStock]:
    """Get all concept memberships for a stock code."""
    return (
        session.query(ThemeMemberStock)
        .filter(ThemeMemberStock.code == code)
        .order_by(ThemeMemberStock.concept_name)
        .all()
    )


def get_members_for_concept(
    *, session: Session, concept_id: str
) -> list[ThemeMemberStock]:
    """Get all member stocks for a concept."""
    return (
        session.query(ThemeMemberStock)
        .filter(ThemeMemberStock.concept_id == concept_id)
        .all()
    )
