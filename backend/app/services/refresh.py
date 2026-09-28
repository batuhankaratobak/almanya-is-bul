"""Manual job refresh orchestration using source manager + normalize/score/dedupe."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_mvp_refresh_queries
from app.models import Job
from app.schemas.jobs import RefreshResponse, SourceRefreshStat
from app.services.deduplication import upsert_normalized_job
from app.services.source_health import load_health, record_refresh_health, resolve_display_status
from app.sources import SourceManager, create_default_source_manager
from app.sources.arbeitsagentur import ArbeitsagenturSource
from app.sources.arbeitnow import ArbeitnowSource


def refresh_jobs(
    db: Session,
    *,
    manager: Optional[SourceManager] = None,
    search_terms: Optional[List[str]] = None,
) -> RefreshResponse:
    """
    Fetch from registered sources, then normalize/score/dedupe any jobs returned.

    Uses the limited MVP refresh query set by default (not every search term).
    """
    manager = manager or create_default_source_manager()
    _prepare_arbeitsagentur_skip_details(db, manager)
    _prepare_arbeitnow_known_ids(db, manager)
    terms = search_terms if search_terms is not None else get_mvp_refresh_queries()
    fetch_result = manager.fetch_all(terms)

    new_jobs = 0
    duplicates = 0
    updated_jobs = 0
    excellent_matches = 0

    for job in fetch_result.jobs:
        result = upsert_normalized_job(db, job)
        if result.action == "new":
            new_jobs += 1
        elif result.action == "cross_source_duplicate":
            duplicates += 1
        elif result.action == "exact_duplicate":
            duplicates += 1
        elif result.action == "updated_existing":
            updated_jobs += 1

        if result.job is not None and (result.job.match_score or 0) >= 80:
            excellent_matches += 1

    source_stats: Dict[str, SourceRefreshStat] = {}
    raw_stats = fetch_result.source_stats()
    for name, payload in raw_stats.items():
        source_stats[name] = SourceRefreshStat(
            status=str(payload.get("status", "failed")),
            jobs_found=int(payload.get("jobs_found") or 0),
            error=payload.get("error") if isinstance(payload.get("error"), str) else None,
            duration_seconds=float(payload.get("duration_seconds") or 0.0),
        )

    record_refresh_health(raw_stats)

    return RefreshResponse(
        status="completed",
        jobs_scanned=len(fetch_result.jobs),
        new_jobs=new_jobs,
        duplicates=duplicates,
        updated_jobs=updated_jobs,
        excellent_matches=excellent_matches,
        duration_seconds=round(float(fetch_result.duration_seconds), 3),
        sources=source_stats,
    )


def list_registered_sources(manager: Optional[SourceManager] = None) -> List[dict]:
    manager = manager or create_default_source_manager()
    health = load_health()
    return [
        {
            "name": source.name,
            "enabled": bool(source.enabled),
            "implemented": bool(source.implemented),
            "status": resolve_display_status(
                name=source.name,
                enabled=bool(source.enabled),
                implemented=bool(source.implemented),
                health=health,
            ),
            "last_error": (health.get(source.name) or {}).get("error"),
            "last_duration_seconds": (health.get(source.name) or {}).get("duration_seconds"),
            "last_success_at": (health.get(source.name) or {}).get("last_success_at"),
            "raw_jobs": (health.get(source.name) or {}).get("raw_jobs"),
            "accepted_jobs": (health.get(source.name) or {}).get("accepted_jobs"),
        }
        for source in manager.get_sources()
    ]


def _prepare_arbeitsagentur_skip_details(db: Session, manager: SourceManager) -> None:
    """Skip detail downloads for Arbeitsagentur jobs we already store with text."""
    known: Set[str] = set(
        db.scalars(
            select(Job.source_job_id).where(
                Job.source == "Arbeitsagentur",
                Job.source_job_id.is_not(None),
                Job.description.is_not(None),
                Job.description != "",
            )
        ).all()
    )
    for source in manager.get_sources():
        if isinstance(source, ArbeitsagenturSource):
            source.skip_detail_ids = {str(value) for value in known if value}


def _prepare_arbeitnow_known_ids(db: Session, manager: SourceManager) -> None:
    """Prefer new Arbeitnow listings when many IDs are already stored."""
    known: Set[str] = set(
        db.scalars(
            select(Job.source_job_id).where(
                Job.source == "Arbeitnow",
                Job.source_job_id.is_not(None),
            )
        ).all()
    )
    for source in manager.get_sources():
        if isinstance(source, ArbeitnowSource):
            source.skip_known_ids = {str(value) for value in known if value}
