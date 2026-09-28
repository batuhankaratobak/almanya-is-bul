"""Additional source references for a logical job (cross-source duplicates)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobSourceReference(Base):
    """Tracks another source where the same logical job was seen."""

    __tablename__ = "job_source_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_job_id",
            name="uq_job_source_refs_source_source_job_id",
        ),
        Index("ix_job_source_refs_job_id", "job_id"),
        Index("ix_job_source_refs_job_url", "job_url"),
        Index("ix_job_source_refs_source", "source"),
    )
