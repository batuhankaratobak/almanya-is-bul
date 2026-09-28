"""EURES (European Employment Services) job source — public JSON search API."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence

from app.config.scoring_profile import DEFAULT_SCORING_PROFILE
from app.services.normalization import normalize_eures_job
from app.sources.base import JobSource
from app.sources.eures_client import (
    EuresClient,
    EuresClientError,
    build_job_url,
    extract_search_results,
)
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


def _dedupe_terms(search_terms: List[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for term in search_terms:
        normalized = (term or "").strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


class EuresSource(JobSource):
    """
    Real source using the publicly reachable EURES JSON API:

    POST https://europa.eu/eures/api/jv-searchengine/public/jv-search/search

    Germany-only via locationCodes=["de"]. No API key required.
    """

    def __init__(
        self,
        client: Optional[EuresClient] = None,
        *,
        max_results_per_query: Optional[int] = None,
        max_total_jobs: Optional[int] = None,
        search_concurrency: Optional[int] = None,
        target_categories: Optional[Sequence[str]] = None,
    ) -> None:
        self.client = client or EuresClient()
        self.max_results_per_query = max(
            1,
            max_results_per_query
            if max_results_per_query is not None
            else _env_int("EURES_MAX_RESULTS_PER_QUERY", 8),
        )
        self.max_total_jobs = max(
            1,
            max_total_jobs
            if max_total_jobs is not None
            else _env_int("EURES_MAX_TOTAL_JOBS", 40),
        )
        self.search_concurrency = max(
            1,
            search_concurrency
            if search_concurrency is not None
            else _env_int("EURES_SEARCH_CONCURRENCY", 3),
        )
        self.target_categories = tuple(
            target_categories or DEFAULT_SCORING_PROFILE.target_categories
        )

    @property
    def name(self) -> str:
        return "EURES"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        terms = _dedupe_terms(search_terms)
        if not terms:
            return []

        collected: Dict[str, Dict[str, Any]] = {}
        errors: List[Exception] = []

        def _search(term: str) -> List[Dict[str, Any]]:
            payload = self.client.search_jobs(
                term,
                page=1,
                results_per_page=min(self.max_results_per_query, 25),
                location_codes=["de"],
            )
            return extract_search_results(payload)

        workers = min(self.search_concurrency, len(terms))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_search, term): term for term in terms}
            for future in as_completed(futures):
                term = futures[future]
                try:
                    rows = future.result()
                except EuresClientError as exc:
                    errors.append(exc)
                    logger.warning("EURES search failed for %r: %s", term, exc)
                    continue
                for item in rows:
                    mapped = map_eures_raw(item)
                    job_id = mapped.get("source_job_id")
                    if not job_id or job_id in collected:
                        continue
                    if not is_germany_relevant(mapped):
                        continue
                    if not matches_target_role(mapped, search_terms, self.target_categories):
                        continue
                    collected[str(job_id)] = mapped
                    if len(collected) >= self.max_total_jobs:
                        break
                if len(collected) >= self.max_total_jobs:
                    break

        if not collected and errors:
            raise errors[0]

        jobs: List[NormalizedJob] = []
        for raw in collected.values():
            try:
                jobs.append(normalize_eures_job(raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed EURES job: %s", exc)
        return jobs


def map_eures_raw(item: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(item.get("id") or "").strip()
    employer = item.get("employer") if isinstance(item.get("employer"), dict) else {}
    company = employer.get("name") or ""
    location = _location_from_map(item.get("locationMap"))
    description = item.get("description")
    if description is None:
        description = ""
    return {
        "source_job_id": job_id,
        "title": item.get("title") or "",
        "company": company,
        "location": location,
        "country": "DE",
        "description": description,
        "job_url": build_job_url(job_id) if job_id else "",
        "date_posted": _millis_to_iso(item.get("creationDate") or item.get("lastModificationDate")),
        "employment_type": _employment_type(item),
        "raw_search": item,
    }


def _location_from_map(location_map: Any) -> str:
    if not isinstance(location_map, dict) or not location_map:
        return "Germany"
    # Prefer DE codes; values are often NUTS region lists.
    if "DE" in location_map:
        regions = location_map.get("DE")
        if isinstance(regions, list) and regions:
            return f"Germany ({regions[0]})"
        return "Germany"
    # Fallback: first country key.
    country = next(iter(location_map.keys()))
    return str(country)


def _millis_to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return str(value)
    # Keep as epoch millis string; normalize_raw_job/dateutil can parse ISO better.
    # Convert to ISO-ish UTC.
    from datetime import datetime, timezone

    return datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc).isoformat()


def _employment_type(item: Dict[str, Any]) -> str:
    codes = item.get("positionScheduleCodes")
    if isinstance(codes, list) and codes:
        return str(codes[0])
    offering = item.get("positionOfferingCode")
    return str(offering or "")
