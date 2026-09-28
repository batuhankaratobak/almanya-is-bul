"""Duplicate detection and safe merge for normalized jobs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobSourceReference
from app.sources.normalized_job import NormalizedJob

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s+&./-]", re.UNICODE)
_GENDER_SUFFIX_RE = re.compile(
    r"""(?ix)
    (?:
        [\(\[]\s*(?:m\s*/\s*w\s*/\s*d|m\s*/\s*w\s*/\s*x|w\s*/\s*m\s*/\s*d|
        m\s*/\s*f\s*/\s*d|d\s*/\s*w\s*/\s*m|w\s*/\s*d\s*/\s*m|
        all\s*genders?)\s*[\)\]]
        |
        \b(?:m\s*/\s*w\s*/\s*d|m\s*/\s*w\s*/\s*x|w\s*/\s*m\s*/\s*d|
        m\s*/\s*f\s*/\s*d|all\s*genders?)\b
    )
    """
)
_COMPANY_SUFFIX_RE = re.compile(
    r"\b(gmbh|ag|kg|ug|se|ltd|llc|inc|co\.?|company)\b\.?",
    re.IGNORECASE,
)


@dataclass
class DedupResult:
    action: str
    job_id: int
    source_reference_added: bool = False
    job: Optional[Job] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "job_id": self.job_id,
            "source_reference_added": self.source_reference_added,
        }


def normalize_company_for_dedup(company: str) -> str:
    text = (company or "").casefold().replace("\u00a0", " ").strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    # Keep legal forms, but normalize spacing/dots around common suffixes.
    text = _COMPANY_SUFFIX_RE.sub(lambda match: match.group(1).casefold(), text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_title_for_dedup(title: str) -> str:
    text = (title or "").casefold().replace("\u00a0", " ").strip()
    text = _GENDER_SUFFIX_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -|/")
    return text


def normalize_location_for_dedup(location: str) -> str:
    text = (location or "").casefold().replace("\u00a0", " ").strip()
    text = _WHITESPACE_RE.sub(" ", text)
    for suffix in (
        ", germany",
        ", deutschland",
        ", de",
        " germany",
        " deutschland",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].rstrip(" ,")
            break
    if text.endswith(" de") and len(text) > 3:
        text = text[:-3].rstrip(" ,")
    text = _PUNCT_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip(" ,")


def normalize_url_for_dedup(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return raw.casefold().rstrip("/")
    normalized = parsed._replace(
        scheme=parsed.scheme.casefold(),
        netloc=parsed.netloc.casefold(),
        fragment="",
        path=parsed.path.rstrip("/") or "",
    )
    return urlunparse(normalized)


def build_fingerprint(company: str, title: str, location: str) -> str:
    payload = "|".join(
        (
            normalize_company_for_dedup(company),
            normalize_title_for_dedup(title),
            normalize_location_for_dedup(location),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def titles_are_safe_to_merge(existing_title: str, incoming_title: str) -> bool:
    """Prefer false negatives: refuse seniority/lead mismatches."""
    left = normalize_title_for_dedup(existing_title)
    right = normalize_title_for_dedup(incoming_title)
    if left == right:
        return True

    seniority = ("senior", "lead", "principal", "staff", "team lead", "teamleiter")
    left_has = any(token in left for token in seniority)
    right_has = any(token in right for token in seniority)
    if left_has != right_has:
        return False
    if left_has and right_has and left != right:
        return False
    return False


def upsert_normalized_job(db: Session, incoming: NormalizedJob) -> DedupResult:
    """
    Insert or merge a normalized job.

    Actions:
    - new
    - exact_duplicate
    - cross_source_duplicate
    - updated_existing
    """
    now = datetime.now(timezone.utc)
    fingerprint = build_fingerprint(incoming.company, incoming.title, incoming.location)
    incoming_url = normalize_url_for_dedup(incoming.job_url)

    existing, match_kind = _find_existing(db, incoming, fingerprint, incoming_url)
    if existing is None:
        job = _create_job(db, incoming, fingerprint, now)
        db.commit()
        db.refresh(job)
        return DedupResult(action="new", job_id=job.id, job=job)

    original_status = existing.status
    source_reference_added = _ensure_source_reference(db, existing, incoming, now)
    _update_existing_job(existing, incoming, fingerprint, now)
    # Never reset application status.
    existing.status = original_status
    db.commit()
    db.refresh(existing)

    if match_kind == "source_id":
        action = "exact_duplicate"
    elif match_kind in {"fingerprint", "url"} and incoming.source != existing.source:
        action = "cross_source_duplicate"
    elif source_reference_added:
        action = "cross_source_duplicate"
    else:
        action = "updated_existing"

    return DedupResult(
        action=action,
        job_id=existing.id,
        source_reference_added=source_reference_added,
        job=existing,
    )


def _find_existing(
    db: Session,
    incoming: NormalizedJob,
    fingerprint: str,
    incoming_url: str,
) -> tuple[Optional[Job], Optional[str]]:
    # 1) Strong: source + source_job_id on primary job
    if incoming.source_job_id:
        job = db.scalar(
            select(Job).where(
                Job.source == incoming.source,
                Job.source_job_id == incoming.source_job_id,
            )
        )
        if job is not None:
            return job, "source_id"

        ref = db.scalar(
            select(JobSourceReference).where(
                JobSourceReference.source == incoming.source,
                JobSourceReference.source_job_id == incoming.source_job_id,
            )
        )
        if ref is not None:
            parent = db.get(Job, ref.job_id)
            if parent is not None:
                return parent, "source_id"

    # 2) Strong: canonical URL
    if incoming_url:
        job = db.scalar(select(Job).where(Job.job_url == incoming.job_url))
        if job is None:
            # Compare normalized forms in Python for robustness.
            candidates = db.scalars(select(Job).where(Job.job_url != "")).all()
            for candidate in candidates:
                if normalize_url_for_dedup(candidate.job_url) == incoming_url:
                    job = candidate
                    break
        if job is not None:
            return job, "url"

        refs = db.scalars(
            select(JobSourceReference).where(JobSourceReference.job_url != "")
        ).all()
        for ref in refs:
            if normalize_url_for_dedup(ref.job_url) == incoming_url:
                parent = db.get(Job, ref.job_id)
                if parent is not None:
                    return parent, "url"

    # 3) Soft: fingerprint across sources only (same company/title/location)
    if fingerprint and normalize_company_for_dedup(incoming.company):
        matches = db.scalars(select(Job).where(Job.fingerprint == fingerprint)).all()
        for job in matches:
            # Same source with different source_job_id → do not merge.
            if job.source == incoming.source and incoming.source_job_id and job.source_job_id:
                if job.source_job_id != incoming.source_job_id:
                    continue
            if not titles_are_safe_to_merge(job.title, incoming.title):
                continue
            if (
                normalize_company_for_dedup(job.company)
                == normalize_company_for_dedup(incoming.company)
                and normalize_title_for_dedup(job.title)
                == normalize_title_for_dedup(incoming.title)
                and normalize_location_for_dedup(job.location)
                == normalize_location_for_dedup(incoming.location)
            ):
                return job, "fingerprint"

    return None, None


def _create_job(
    db: Session,
    incoming: NormalizedJob,
    fingerprint: str,
    now: datetime,
) -> Job:
    job = Job(
        source=incoming.source,
        source_job_id=incoming.source_job_id,
        title=incoming.title,
        company=incoming.company,
        location=incoming.location,
        country=getattr(incoming, "country", None) or "DE",
        description=incoming.description or "",
        job_url=incoming.job_url or "",
        application_url=getattr(incoming, "application_url", None)
        or incoming.job_url
        or "",
        date_posted=incoming.date_posted,
        first_seen_at=incoming.first_seen_at or now,
        last_seen_at=incoming.last_seen_at or now,
        remote=bool(incoming.remote),
        hybrid=bool(incoming.hybrid),
        employment_type=incoming.employment_type,
        job_language=incoming.job_language,
        german_requirement=incoming.german_requirement,
        english_requirement=incoming.english_requirement,
        experience_level=incoming.experience_level,
        match_score=incoming.match_score or 0,
        match_category=incoming.match_category,
        role_family=(incoming.raw or {}).get("role_family"),
        discovery_relevance=(incoming.raw or {}).get("discovery_relevance"),
        classification_json=_classification_json(incoming),
        fingerprint=fingerprint,
        status=incoming.status or "new",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()
    return job


def _ensure_source_reference(
    db: Session,
    existing: Job,
    incoming: NormalizedJob,
    now: datetime,
) -> bool:
    """Add a source reference when the incoming source is new for this job."""
    if (
        existing.source == incoming.source
        and (existing.source_job_id or None) == (incoming.source_job_id or None)
    ):
        return False

    if existing.source == incoming.source and not incoming.source_job_id:
        return False

    # Already tracked as primary.
    if existing.source == incoming.source and existing.source_job_id == incoming.source_job_id:
        return False

    # Already tracked as additional reference?
    existing_refs = db.scalars(
        select(JobSourceReference).where(JobSourceReference.job_id == existing.id)
    ).all()
    for ref in existing_refs:
        same_source = ref.source == incoming.source
        same_id = (ref.source_job_id or None) == (incoming.source_job_id or None)
        same_url = (
            normalize_url_for_dedup(ref.job_url) == normalize_url_for_dedup(incoming.job_url)
            and bool(incoming.job_url)
        )
        if same_source and (same_id or same_url):
            ref.last_seen_at = now
            if incoming.job_url and not ref.job_url:
                ref.job_url = incoming.job_url
            return False

    # Different source (or same source with new identifier) → preserve it.
    if incoming.source != existing.source or (
        incoming.source_job_id and incoming.source_job_id != existing.source_job_id
    ):
        # Avoid unique constraint clash if this source_job_id already points elsewhere.
        if incoming.source_job_id:
            clash = db.scalar(
                select(JobSourceReference).where(
                    JobSourceReference.source == incoming.source,
                    JobSourceReference.source_job_id == incoming.source_job_id,
                )
            )
            if clash is not None:
                clash.last_seen_at = now
                return False

        db.add(
            JobSourceReference(
                job_id=existing.id,
                source=incoming.source,
                source_job_id=incoming.source_job_id,
                job_url=incoming.job_url or "",
                first_seen_at=now,
                last_seen_at=now,
            )
        )
        return True
    return False


def _update_existing_job(
    existing: Job,
    incoming: NormalizedJob,
    fingerprint: str,
    now: datetime,
) -> None:
    existing.last_seen_at = now
    existing.updated_at = now
    if fingerprint and not existing.fingerprint:
        existing.fingerprint = fingerprint

    if incoming.description and (
        not existing.description or len(incoming.description) > len(existing.description)
    ):
        existing.description = incoming.description

    if existing.date_posted is None and incoming.date_posted is not None:
        existing.date_posted = incoming.date_posted

    if incoming.remote:
        existing.remote = True
    if incoming.hybrid:
        existing.hybrid = True

    if incoming.employment_type and not existing.employment_type:
        existing.employment_type = incoming.employment_type

    if incoming.job_language and not existing.job_language:
        existing.job_language = incoming.job_language

    existing.german_requirement = _prefer_language_requirement(
        existing.german_requirement, incoming.german_requirement
    )
    existing.english_requirement = _prefer_language_requirement(
        existing.english_requirement, incoming.english_requirement
    )

    if incoming.experience_level and (
        not existing.experience_level or existing.experience_level == "unknown"
    ):
        existing.experience_level = incoming.experience_level

    if incoming.match_score and incoming.match_score > (existing.match_score or 0):
        existing.match_score = incoming.match_score
        if incoming.match_category:
            existing.match_category = incoming.match_category

    classification = (incoming.raw or {}).get("classification")
    if classification:
        existing.role_family = (incoming.raw or {}).get("role_family") or existing.role_family
        existing.discovery_relevance = (
            (incoming.raw or {}).get("discovery_relevance") or existing.discovery_relevance
        )
        existing.classification_json = _classification_json(incoming) or existing.classification_json

    if incoming.job_url and not existing.job_url:
        existing.job_url = incoming.job_url

    app_url = getattr(incoming, "application_url", None) or ""
    if app_url and not getattr(existing, "application_url", None):
        existing.application_url = app_url

    country = getattr(incoming, "country", None) or ""
    if country and (not getattr(existing, "country", None) or existing.country == "DE"):
        # Prefer an explicit non-default country when merging.
        if country != "DE" or not existing.country:
            existing.country = country


def _classification_json(incoming: NormalizedJob) -> Optional[str]:
    import json

    payload = (incoming.raw or {}).get("classification")
    if not payload:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def _prefer_language_requirement(existing: Optional[str], incoming: Optional[str]) -> Optional[str]:
    if not incoming:
        return existing
    if not existing:
        return incoming
    # Prefer concrete levels / clearer statuses over unknown/null.
    if existing.startswith("null|") and not incoming.startswith("null|"):
        return incoming
    if existing.endswith("|unknown") and not incoming.endswith("|unknown"):
        return incoming
    return existing


def list_source_links(db: Session, job: Job) -> list[dict]:
    """Return primary + additional source references for a job."""
    links = [
        {
            "source": job.source,
            "source_job_id": job.source_job_id,
            "job_url": job.job_url,
            "first_seen_at": job.first_seen_at,
            "last_seen_at": job.last_seen_at,
            "primary": True,
        }
    ]
    refs = db.scalars(
        select(JobSourceReference).where(JobSourceReference.job_id == job.id)
    ).all()
    for ref in refs:
        links.append(
            {
                "source": ref.source,
                "source_job_id": ref.source_job_id,
                "job_url": ref.job_url,
                "first_seen_at": ref.first_seen_at,
                "last_seen_at": ref.last_seen_at,
                "primary": False,
            }
        )
    return links
