"""Request/response schemas for job-related endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.status import ApplicationStatus


class SourceReferenceOut(BaseModel):
    source: str
    source_job_id: Optional[str] = None
    job_url: str = ""
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    primary: bool = False


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str
    country: str = "DE"
    description: str
    primary_source: str
    source_references: List[SourceReferenceOut] = Field(default_factory=list)
    job_url: str
    application_url: Optional[str] = None
    date_posted: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    remote: bool
    hybrid: bool
    employment_type: Optional[str] = None
    job_language: Optional[str] = None
    german_requirement: Optional[str] = None
    english_requirement: Optional[str] = None
    experience_level: Optional[str] = None
    category: str
    role_family: Optional[str] = None
    discovery_relevance: Optional[str] = None
    match_score: int
    match_category: Optional[str] = None
    status: str
    positive_reasons: List[str] = Field(default_factory=list)
    negative_reasons: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)


class JobListResponse(BaseModel):
    items: List[JobOut]
    total: int
    limit: int
    offset: int


class JobStatusUpdate(BaseModel):
    status: ApplicationStatus


class StatsResponse(BaseModel):
    total_jobs: int
    excellent_matches: int
    good_matches: int
    possible_matches: int
    poor_matches: int
    new: int
    reviewing: int
    applied: int
    interviews: int
    rejected: int
    ignored: int
    offers: int


class SourceInfo(BaseModel):
    name: str
    enabled: bool
    implemented: bool
    status: str = "idle"
    last_error: Optional[str] = None
    last_duration_seconds: Optional[float] = None
    last_success_at: Optional[str] = None
    raw_jobs: Optional[int] = None
    accepted_jobs: Optional[int] = None


class SourcesResponse(BaseModel):
    sources: List[SourceInfo]


class SourceRefreshStat(BaseModel):
    status: str
    jobs_found: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


class RefreshResponse(BaseModel):
    status: str
    jobs_scanned: int
    new_jobs: int
    duplicates: int
    updated_jobs: int
    excellent_matches: int
    duration_seconds: float = 0.0
    sources: Dict[str, SourceRefreshStat]
