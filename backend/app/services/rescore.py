"""Locally rescore and reclassify all stored jobs against the candidate profile."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.candidate_profile import load_profile
from app.services.job_query import _as_normalized
from app.services.role_classifier import classify_job
from app.services.scoring import apply_score


def rescore_all_jobs(db: Session, profile: Optional[Dict[str, Any]] = None) -> dict:
    """
    Recalculate match_score / match_category / role classification for every job.

    Does not touch application status or delete rows.
    """
    profile = profile or load_profile()
    jobs = list(db.scalars(select(Job)).all())
    updated = 0
    discovery_counts = {"high": 0, "medium": 0, "low": 0}
    family_changes = 0
    for job in jobs:
        previous_family = job.role_family
        previous_status = job.status
        normalized = _as_normalized(job)
        result = apply_score(normalized, profile=profile)
        classification = classify_job(job.title or "", job.description or "")

        changed = (
            (job.match_score or 0) != result.score
            or (job.match_category or "") != result.category
            or (job.role_family or "") != classification.primary_role_family
            or (job.discovery_relevance or "") != classification.discovery_relevance
        )
        job.match_score = result.score
        job.match_category = result.category
        job.role_family = classification.primary_role_family
        job.discovery_relevance = classification.discovery_relevance
        job.classification_json = classification.to_json()
        # Hard guarantee: never reset application status during rescore.
        job.status = previous_status
        if previous_family and previous_family != classification.primary_role_family:
            family_changes += 1
        discovery_counts[classification.discovery_relevance] = (
            discovery_counts.get(classification.discovery_relevance, 0) + 1
        )
        if changed:
            updated += 1
    db.commit()
    return {
        "jobs_total": len(jobs),
        "jobs_updated": updated,
        "family_changes": family_changes,
        "discovery_high": discovery_counts.get("high", 0),
        "discovery_medium": discovery_counts.get("medium", 0),
        "discovery_low": discovery_counts.get("low", 0),
        "profile_skills": len(profile.get("skills") or []),
        "statuses_preserved": True,
    }
