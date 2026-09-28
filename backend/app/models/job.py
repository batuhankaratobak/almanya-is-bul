"""Job ORM model matching PROJECT_SPEC.md."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.status import ApplicationStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    """Normalized job listing stored locally."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(8), nullable=False, default="DE")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    job_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    application_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    date_posted: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hybrid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    employment_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    job_language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    german_requirement: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    english_requirement: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    match_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Role taxonomy classification (discovery ≠ candidate match score).
    role_family: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    discovery_relevance: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    classification_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deterministic duplicate key: sha256(norm_company|norm_title|norm_location)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ApplicationStatus.NEW.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
        Index("ix_jobs_job_url", "job_url"),
        Index("ix_jobs_company_title_location", "company", "title", "location"),
        Index("ix_jobs_fingerprint", "fingerprint"),
        Index("ix_jobs_source_job_id", "source_job_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_match_score", "match_score"),
        Index("ix_jobs_job_language", "job_language"),
        Index("ix_jobs_location", "location"),
        Index("ix_jobs_source", "source"),
        Index("ix_jobs_german_requirement", "german_requirement"),
        Index("ix_jobs_remote", "remote"),
    )
