"""Arbeitnow job source (public job-board JSON API)."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Set

from app.config.scoring_profile import DEFAULT_SCORING_PROFILE
from app.services.normalization import normalize_arbeitnow_job
from app.sources.arbeitnow_client import (
    ArbeitnowClient,
    ArbeitnowClientError,
    extract_jobs,
    has_next_page,
)
from app.sources.base import JobSource
from app.sources.filters import is_germany_relevant, matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class ArbeitnowSource(JobSource):
    """
    Real source using the public Arbeitnow feed:

    GET https://www.arbeitnow.com/api/job-board-api?page={n}

    No API key. Broad feed → local Germany + discovery-role filtering.
    """

    def __init__(
        self,
        client: Optional[ArbeitnowClient] = None,
        *,
        max_pages: Optional[int] = None,
        max_jobs: Optional[int] = None,
        target_categories: Optional[Sequence[str]] = None,
        skip_known_ids: Optional[Set[str]] = None,
    ) -> None:
        self.client = client or ArbeitnowClient()
        self.max_pages = max(1, max_pages if max_pages is not None else _env_int("ARBEITNOW_MAX_PAGES", 2))
        self.max_jobs = max(1, max_jobs if max_jobs is not None else _env_int("ARBEITNOW_MAX_JOBS", 80))
        self.target_categories = tuple(
            target_categories or DEFAULT_SCORING_PROFILE.target_categories
        )
        self.skip_known_ids = set(skip_known_ids or set())
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Arbeitnow"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        collected: Dict[str, Dict[str, Any]] = {}
        page = 1
        raw_seen = 0
        while page <= self.max_pages and len(collected) < self.max_jobs:
            try:
                payload = self.client.fetch_page(page)
            except ArbeitnowClientError:
                raise

            rows = extract_jobs(payload)
            if not rows:
                break
            raw_seen += len(rows)

            for item in rows:
                mapped = map_arbeitnow_raw(item)
                key = str(mapped.get("slug") or mapped.get("source_job_id") or "")
                if not key:
                    continue
                if not is_germany_relevant(item):
                    continue
                if not matches_target_role(item, search_terms, self.target_categories):
                    continue
                # Prefer unseen listings when the page budget is tight.
                if key in self.skip_known_ids and len(collected) >= max(15, self.max_jobs // 2):
                    continue
                collected[key] = mapped
                if len(collected) >= self.max_jobs:
                    break

            if not has_next_page(payload, page):
                break
            page += 1

        jobs: List[NormalizedJob] = []
        for raw in collected.values():
            try:
                jobs.append(normalize_arbeitnow_job(raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed Arbeitnow job: %s", exc)
        self.last_raw_jobs = raw_seen
        self.last_accepted_jobs = len(jobs)
        return jobs


def map_arbeitnow_raw(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map Arbeitnow API fields into normalize_arbeitnow_job input."""
    slug = item.get("slug")
    source_job_id = slug or item.get("id")
    job_types = item.get("job_types") if isinstance(item.get("job_types"), list) else []
    return {
        "slug": slug,
        "id": item.get("id"),
        "source_job_id": source_job_id,
        "title": item.get("title") or "",
        "company_name": item.get("company_name") or item.get("company") or "",
        "location": item.get("location") or "",
        "description": item.get("description") or "",
        "url": item.get("url") or item.get("job_url") or "",
        "created_at": item.get("created_at") or item.get("date_posted"),
        "remote": bool(item.get("remote")),
        "job_types": job_types,
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
    }
