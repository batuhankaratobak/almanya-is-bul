"""Query helpers and response mapping for jobs API."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.config.search_terms import list_categories
from app.models import Job, JobSourceReference
from app.schemas.jobs import JobOut, SourceReferenceOut
from app.services.deduplication import list_source_links
from app.services.role_classifier import job_matches_filter_category
from app.services.scoring import detect_role_category, score_job
from app.sources.normalized_job import NormalizedJob

VALID_CATEGORIES = set(list_categories()) | {
    "software_development",
    "it_support",
    "cybersecurity",
    "qa_testing",
    "system_administration",
    "application_support",
    "it_consulting",
}

VALID_LANGUAGES = {"de", "en", "de/en", "unknown"}
VALID_GERMAN_LEVELS = {
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
    "required",
    "preferred",
    "not_required",
    "unknown",
}
VALID_WORK_MODELS = {"remote", "hybrid", "onsite"}
VALID_SORTS = {"score", "newest", "oldest"}


def serialize_job(db: Session, job: Job, *, include_reasons: bool = True) -> JobOut:
    links = list_source_links(db, job)
    category = detect_role_category(job.title or "", job.description or "")
    positive: List[str] = []
    negative: List[str] = []
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    if include_reasons:
        scored = score_job(_as_normalized(job))
        positive = scored.positive_reasons
        negative = scored.negative_reasons
        matched_skills = scored.matched_skills
        missing_skills = scored.missing_skills
        category = scored.role_category or category

    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        country=getattr(job, "country", None) or "DE",
        description=job.description,
        primary_source=job.source,
        source_references=[SourceReferenceOut(**link) for link in links],
        job_url=job.job_url,
        application_url=getattr(job, "application_url", None) or job.job_url,
        date_posted=job.date_posted,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        remote=bool(job.remote),
        hybrid=bool(job.hybrid),
        employment_type=job.employment_type,
        job_language=job.job_language,
        german_requirement=job.german_requirement,
        english_requirement=job.english_requirement,
        experience_level=job.experience_level,
        category=category,
        role_family=getattr(job, "role_family", None),
        discovery_relevance=getattr(job, "discovery_relevance", None),
        match_score=job.match_score or 0,
        match_category=job.match_category,
        status=job.status,
        positive_reasons=positive,
        negative_reasons=negative,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )


def list_jobs(
    db: Session,
    *,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    german_level: Optional[str] = None,
    work_model: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "score",
) -> Tuple[List[JobOut], int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    sort = sort if sort in VALID_SORTS else "score"

    if category is not None and category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'")
    if language is not None and language not in VALID_LANGUAGES:
        raise ValueError(f"Invalid language '{language}'")
    if german_level is not None and german_level not in VALID_GERMAN_LEVELS:
        raise ValueError(f"Invalid german_level '{german_level}'")
    if work_model is not None and work_model not in VALID_WORK_MODELS:
        raise ValueError(f"Invalid work_model '{work_model}'")
    if (
        min_score is not None
        and max_score is not None
        and min_score > max_score
    ):
        raise ValueError("min_score cannot be greater than max_score")

    stmt = select(Job)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(term),
                Job.company.ilike(term),
                Job.description.ilike(term),
            )
        )
    if status:
        stmt = stmt.where(Job.status == status)
    if language:
        stmt = stmt.where(Job.job_language == language)
    if min_score is not None:
        stmt = stmt.where(Job.match_score >= min_score)
    if max_score is not None:
        stmt = stmt.where(Job.match_score <= max_score)
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location.strip()}%"))
    if country:
        stmt = stmt.where(Job.country == country.strip().upper())
    if work_model == "remote":
        stmt = stmt.where(Job.remote.is_(True))
    elif work_model == "hybrid":
        stmt = stmt.where(Job.hybrid.is_(True))
    elif work_model == "onsite":
        stmt = stmt.where(Job.remote.is_(False), Job.hybrid.is_(False))

    if german_level:
        if german_level in {"A1", "A2", "B1", "B2", "C1", "C2"}:
            stmt = stmt.where(Job.german_requirement.ilike(f"{german_level}|%"))
        else:
            stmt = stmt.where(Job.german_requirement.ilike(f"%|{german_level}"))

    if source:
        ref_job_ids = select(JobSourceReference.job_id).where(
            JobSourceReference.source == source
        )
        stmt = stmt.where(or_(Job.source == source, Job.id.in_(ref_job_ids)))

    if sort == "newest":
        stmt = stmt.order_by(
            desc(func.coalesce(Job.date_posted, Job.first_seen_at)),
            desc(Job.first_seen_at),
            desc(Job.id),
        )
    elif sort == "oldest":
        stmt = stmt.order_by(
            asc(func.coalesce(Job.date_posted, Job.first_seen_at)),
            asc(Job.first_seen_at),
            asc(Job.id),
        )
    else:
        stmt = stmt.order_by(
            desc(Job.match_score),
            desc(func.coalesce(Job.date_posted, Job.first_seen_at)),
            desc(Job.first_seen_at),
            desc(Job.id),
        )

    jobs = list(db.scalars(stmt).all())

    if category:
        jobs = [
            job
            for job in jobs
            if job_matches_filter_category(
                job.title or "", job.description or "", category
            )
        ]

    total = len(jobs)
    page = jobs[offset : offset + limit]
    # List views don't need expensive reason recompute; detail endpoint still scores.
    items = [serialize_job(db, job, include_reasons=False) for job in page]
    return items, total


def get_job_or_none(db: Session, job_id: int) -> Optional[Job]:
    return db.get(Job, job_id)


def update_job_status(db: Session, job: Job, status: str) -> Job:
    job.status = status
    db.commit()
    db.refresh(job)
    return job


def compute_stats(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Job)) or 0

    def count_score(low: int, high: int) -> int:
        return (
            db.scalar(
                select(func.count()).select_from(Job).where(
                    Job.match_score >= low, Job.match_score <= high
                )
            )
            or 0
        )

    def count_status(value: str) -> int:
        return (
            db.scalar(select(func.count()).select_from(Job).where(Job.status == value))
            or 0
        )

    return {
        "total_jobs": total,
        # Calibrated bands: 90+ mükemmel/çok uygun bucket for dashboard "Çok Uygun"
        "excellent_matches": count_score(80, 100),  # Çok Uygun + Mükemmel
        "good_matches": count_score(70, 79),  # Uygun
        "possible_matches": count_score(55, 69),  # Olası
        "poor_matches": count_score(0, 54),  # Düşük Uygunluk
        "new": count_status("new"),
        "reviewing": count_status("reviewing"),
        "applied": count_status("applied"),
        "interviews": count_status("interview"),
        "rejected": count_status("rejected"),
        "ignored": count_status("ignored"),
        "offers": count_status("offer"),
    }


def _as_normalized(job: Job) -> NormalizedJob:
    return NormalizedJob(
        source=job.source,
        source_job_id=job.source_job_id,
        title=job.title,
        company=job.company,
        location=job.location,
        country=getattr(job, "country", None) or "DE",
        description=job.description or "",
        job_url=job.job_url or "",
        application_url=getattr(job, "application_url", None) or job.job_url or "",
        date_posted=job.date_posted,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        remote=bool(job.remote),
        hybrid=bool(job.hybrid),
        employment_type=job.employment_type,
        job_language=job.job_language,
        german_requirement=job.german_requirement,
        english_requirement=job.english_requirement,
        experience_level=job.experience_level,
        match_score=job.match_score or 0,
        match_category=job.match_category,
        status=job.status,
    )
