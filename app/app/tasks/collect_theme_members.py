"""Task wrapper for theme member collection pipeline.

Purpose: Expose collect_theme_members pipeline as a CLI-runnable task.
"""

from __future__ import annotations

from typing import Any

from app.db.session import init_db
from app.pipelines.collect_theme_members import collect_theme_members


def run(concept_ids: list[str] | None = None) -> dict[str, Any]:
    """Run the full THS concept member scrape and upsert.

    Args:
        concept_ids: Optional list of concept IDs to limit the run.
                     If None, fetches all ~362 concepts from THS.

    Returns:
        Summary dict: total, succeeded, failed, skipped, failed_ids.
    """
    init_db()
    return collect_theme_members(concept_ids=concept_ids)
