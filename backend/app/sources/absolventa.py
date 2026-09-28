"""Absolventa source via public sitemap + schema.org JobPosting JSON-LD."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence

from app.config.scoring_profile import DEFAULT_SCORING_PROFILE
from app.services.normalization import normalize_absolventa_job
from app.sources.absolventa_client import (
    AbsolventaClient,
    AbsolventaClientError,
    country_from_job_posting,
    location_from_job_posting,
    source_job_id_from_url,
)
from app.sources.base import JobSource
from app.sources.filters import is_germany_relevant, matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

# URL slug markers that correlate with configured IT categories.
_IT_URL_MARKERS = (
    "software",
    "entwickler",
    "developer",
    "engineer",
    "informatiker",
    "fullstack",
    "full-stack",
    "backend",
    "frontend",
    "devops",
    "systemadmin",
    "system-admin",
    "administrator",
    "it-support",
    "it_support",
    "helpdesk",
    "servicedesk",
    "cyber",
    "security",
    "sicherheit",
    "soc-",
    "qa-",
    "tester",
    "testing",
    "consultant-it",
    "it-consultant",
    "anwendungs",
    "applikation",
)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class AbsolventaSource(JobSource):
    """
    Real source using public Absolventa structured data:

    1. GET https://www.absolventa.de/sitemap-stellen.xml
    2. Filter IT-relevant job URLs
    3. Fetch schema.org JobPosting JSON-LD from detail pages

    No public job-search JSON API is available (employer Pull API only).
    """

    def __init__(
        self,
        client: Optional[AbsolventaClient] = None,
        *,
        max_jobs: Optional[int] = None,
        max_candidate_urls: Optional[int] = None,
        detail_concurrency: Optional[int] = None,
        target_categories: Optional[Sequence[str]] = None,
    ) -> None:
        self.client = client or AbsolventaClient()
        self.max_jobs = max(1, max_jobs if max_jobs is not None else _env_int("ABSOLVENTA_MAX_JOBS", 25))
        self.max_candidate_urls = max(
            1,
            max_candidate_urls
            if max_candidate_urls is not None
            else _env_int("ABSOLVENTA_MAX_CANDIDATE_URLS", 40),
        )
        self.detail_concurrency = max(
            1,
            detail_concurrency
            if detail_concurrency is not None
            else _env_int("ABSOLVENTA_DETAIL_CONCURRENCY", 3),
        )
        self.target_categories = tuple(
            target_categories or DEFAULT_SCORING_PROFILE.target_categories
        )

    @property
    def name(self) -> str:
        return "Absolventa"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        try:
            urls = self.client.fetch_sitemap_urls()
        except AbsolventaClientError:
            raise

        candidates = [url for url in urls if _looks_like_it_job_url(url)]
        candidates = candidates[: self.max_candidate_urls]
        if not candidates:
            return []

        postings: List[Dict[str, Any]] = []
        workers = min(self.detail_concurrency, len(candidates))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._fetch_one, url): url for url in candidates
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    mapped = future.result()
                except AbsolventaClientError as exc:
                    logger.warning("Absolventa detail failed for %s: %s", url, exc)
                    continue
                if not mapped:
                    continue
                if not is_germany_relevant(mapped):
                    continue
                if not matches_target_role(mapped, search_terms, self.target_categories):
                    continue
                postings.append(mapped)
                if len(postings) >= self.max_jobs:
                    break

        jobs: List[NormalizedJob] = []
        for raw in postings[: self.max_jobs]:
            try:
                jobs.append(normalize_absolventa_job(raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed Absolventa job: %s", exc)
        return jobs

    def _fetch_one(self, url: str) -> Optional[Dict[str, Any]]:
        posting = self.client.fetch_job_posting(url)
        if not posting:
            return None
        company = posting.get("hiringOrganization")
        if isinstance(company, dict):
            company_name = company.get("name") or ""
        else:
            company_name = str(company or "")
        employment = posting.get("employmentType")
        if isinstance(employment, list):
            employment_type = str(employment[0]) if employment else ""
        else:
            employment_type = str(employment or "")
        return {
            "source_job_id": source_job_id_from_url(url),
            "title": posting.get("title") or "",
            "company": company_name,
            "location": location_from_job_posting(posting),
            "country": country_from_job_posting(posting),
            "description": posting.get("description") or "",
            "job_url": posting.get("url") or url,
            "date_posted": posting.get("datePosted"),
            "employment_type": employment_type,
            "raw_posting": posting,
        }


def _looks_like_it_job_url(url: str) -> bool:
    if "/stellenangebote/" not in url:
        return False
    hay = url.casefold()
    return any(marker in hay for marker in _IT_URL_MARKERS)
