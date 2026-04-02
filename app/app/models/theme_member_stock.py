"""Theme member stock model.

Purpose: Persist full concept-member mappings from THS, covering all ~362 concepts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ThemeMemberStock(Base):
    """Full membership table for THS concept/theme stocks."""

    __tablename__ = "theme_member_stock"
    __table_args__ = (UniqueConstraint("concept_id", "code", name="uq_theme_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_id: Mapped[str] = mapped_column(String(16), index=True)
    concept_name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_date: Mapped[str] = mapped_column(String(10))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
