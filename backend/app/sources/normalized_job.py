"""Normalized job payload shared by all source adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedJob:
    """Source-agnostic job shape aligned with PROJECT_SPEC.md fields."""

    source: str
    title: str
    company: str = ""
    location: str = ""
    # Compact comparison key for later duplicate detection (not a geocoder).
    location_normalized: str = ""
    country: str = "DE"
    description: str = ""
    job_url: str = ""
    # Best available apply / original listing URL (may equal job_url).
    application_url: str = ""
    source_job_id: Optional[str] = None
    date_posted: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    remote: bool = False
    hybrid: bool = False
    employment_type: Optional[str] = None
    job_language: Optional[str] = None
    german_requirement: Optional[str] = None
    english_requirement: Optional[str] = None
    experience_level: Optional[str] = None
    match_score: int = 0
    match_category: Optional[str] = None
    status: str = "new"
    # Extra diagnostic metadata for later phases (not persisted yet).
    raw: dict = field(default_factory=dict)
