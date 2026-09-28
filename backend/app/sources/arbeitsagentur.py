"""Bundesagentur für Arbeit / Arbeitsagentur job source (real Jobsuche API)."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set

from app.services.normalization import normalize_arbeitsagentur_job
from app.sources.arbeitsagentur_client import (
    ArbeitsagenturClient,
    ArbeitsagenturClientError,
    build_job_url,
    extract_search_results,
)
from app.sources.base import JobSource
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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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


class ArbeitsagenturSource(JobSource):
    """
    Real source using the public Jobsuche REST API:

    GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs
    GET .../pc/v4/jobdetails/{base64(referenznummer)}

    Auth: public X-API-Key `jobboerse-jobsuche` (documented by bundesAPI/jobsuche-api).
    """

    def __init__(
        self,
        client: Optional[ArbeitsagenturClient] = None,
        *,
        max_results_per_query: Optional[int] = None,
        max_total_jobs: Optional[int] = None,
        fetch_details: Optional[bool] = None,
        search_concurrency: Optional[int] = None,
        detail_concurrency: Optional[int] = None,
        skip_detail_ids: Optional[Set[str]] = None,
    ) -> None:
        self.client = client or ArbeitsagenturClient()
        self.max_results_per_query = max(
            1,
            max_results_per_query
            if max_results_per_query is not None
            else _env_int("ARBEITSAGENTUR_MAX_RESULTS_PER_QUERY", 25),
        )
        self.max_total_jobs = max(
            1,
            max_total_jobs
            if max_total_jobs is not None
            else _env_int("ARBEITSAGENTUR_MAX_TOTAL_JOBS", 60),
        )
        # Details are expensive; search payload is enough for daily browsing.
        self.fetch_details = (
            fetch_details
            if fetch_details is not None
            else _env_bool("ARBEITSAGENTUR_FETCH_DETAILS", False)
        )
        self.search_concurrency = max(
            1,
            search_concurrency
            if search_concurrency is not None
            else _env_int("ARBEITSAGENTUR_SEARCH_CONCURRENCY", 3),
        )
        self.detail_concurrency = max(
            1,
            detail_concurrency
            if detail_concurrency is not None
            else _env_int("ARBEITSAGENTUR_DETAIL_CONCURRENCY", 3),
        )
        self.skip_detail_ids = set(skip_detail_ids or ())

    @property
    def name(self) -> str:
        return "Arbeitsagentur"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        terms = _dedupe_terms(search_terms)
        if not terms:
            return []

        collected: Dict[str, Dict[str, Any]] = {}
        page_size = min(self.max_results_per_query, self.max_total_jobs, 50)

        def _search(term: str) -> List[Dict[str, Any]]:
            payload = self.client.search_jobs(term, page=1, size=page_size)
            return extract_search_results(payload)

        workers = min(self.search_concurrency, len(terms))
        errors: List[Exception] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_search, term): term for term in terms}
            for future in as_completed(futures):
                term = futures[future]
                try:
                    items = future.result()
                except ArbeitsagenturClientError as exc:
                    errors.append(exc)
                    logger.warning("Arbeitsagentur search failed for %r: %s", term, exc)
                    continue
                for item in items:
                    if len(collected) >= self.max_total_jobs:
                        break
                    ref = _referenznummer(item)
                    if not ref or ref in collected:
                        continue
                    collected[ref] = item
                if len(collected) >= self.max_total_jobs:
                    # Cancel remaining searches politely by ignoring further results.
                    break

        if not collected and errors:
            # All searches failed — surface as source failure.
            raise errors[0]

        details: Dict[str, Dict[str, Any]] = {}
        if self.fetch_details:
            need_details = [
                ref
                for ref, item in collected.items()
                if ref not in self.skip_detail_ids and not _has_description(item)
            ]
            if need_details:
                details = self._fetch_details_parallel(need_details)

        jobs: List[NormalizedJob] = []
        for ref, item in collected.items():
            detail = details.get(ref)
            raw = map_arbeitsagentur_raw(item, detail=detail)
            try:
                jobs.append(normalize_arbeitsagentur_job(raw))
            except Exception as exc:  # noqa: BLE001 - keep one bad item from killing batch
                logger.warning("Skipping malformed Arbeitsagentur job %s: %s", ref, exc)
        return jobs

    def _fetch_details_parallel(self, refs: List[str]) -> Dict[str, Dict[str, Any]]:
        details: Dict[str, Dict[str, Any]] = {}
        workers = min(self.detail_concurrency, len(refs))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.client.fetch_job_details, ref): ref for ref in refs}
            for future in as_completed(futures):
                ref = futures[future]
                try:
                    details[ref] = future.result()
                except ArbeitsagenturClientError as exc:
                    logger.warning("Arbeitsagentur detail failed for %s: %s", ref, exc)
        return details


def map_arbeitsagentur_raw(
    search_item: Dict[str, Any],
    *,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Map Jobsuche search (+ optional detail) payload into normalize_* input."""
    detail = detail or {}
    ref = _referenznummer(detail) or _referenznummer(search_item)
    title = (
        detail.get("stellenangebotsTitel")
        or detail.get("titel")
        or search_item.get("stellenangebotsTitel")
        or search_item.get("titel")
        or search_item.get("beruf")
        or ""
    )
    company = (
        detail.get("firma")
        or detail.get("arbeitgeber")
        or search_item.get("firma")
        or search_item.get("arbeitgeber")
        or ""
    )
    location = _extract_location(detail) or _extract_location(search_item)
    description = (
        detail.get("stellenangebotsBeschreibung")
        or detail.get("stellenbeschreibung")
        or search_item.get("stellenbeschreibung")
        or search_item.get("stellenangebotsBeschreibung")
        or ""
    )
    if not str(description).strip():
        # Search hits often omit full text; keep taxonomy signals from structured fields.
        bits = []
        for key in ("hauptberuf", "stellenangebotsTitel", "titel"):
            value = detail.get(key) or search_item.get(key)
            if value:
                bits.append(str(value))
        alle = detail.get("alleBerufe") or search_item.get("alleBerufe")
        if isinstance(alle, list):
            bits.extend(str(item) for item in alle if item)
        description = " | ".join(bits)
    date_posted = (
        detail.get("datumErsteVeroeffentlichung")
        or _nested_von(detail.get("veroeffentlichungszeitraum"))
        or search_item.get("datumErsteVeroeffentlichung")
        or search_item.get("aktuelleVeroeffentlichungsdatum")
        or _nested_von(search_item.get("veroeffentlichungszeitraum"))
        or search_item.get("eintrittsdatum")
    )
    employment_type = _employment_type(detail) or _employment_type(search_item)
    externe = (
        detail.get("externeUrl")
        or detail.get("externeURL")
        or search_item.get("externeUrl")
        or search_item.get("externeURL")
    )
    job_url = externe or (build_job_url(ref) if ref else "")
    homeoffice = detail.get("homeofficemoeglich")
    if homeoffice is None:
        homeoffice = search_item.get("homeofficemoeglich")

    return {
        "referenznummer": ref,
        "titel": title,
        "arbeitgeber": company,
        "arbeitsort": location,
        "stellenbeschreibung": description,
        "externeUrl": job_url,
        "aktuelleVeroeffentlichungsdatum": date_posted,
        "arbeitszeit": employment_type,
        "homeofficemoeglich": homeoffice,
        "raw_search": search_item,
        "raw_detail": detail,
    }


def _has_description(item: Dict[str, Any]) -> bool:
    text = item.get("stellenbeschreibung") or item.get("stellenangebotsBeschreibung") or ""
    return bool(str(text).strip())


def _referenznummer(payload: Dict[str, Any]) -> Optional[str]:
    value = payload.get("referenznummer") or payload.get("refnr") or payload.get("id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_location(payload: Dict[str, Any]) -> str:
    locations = payload.get("stellenlokationen") or payload.get("arbeitsorte") or []
    if isinstance(locations, list) and locations:
        first = locations[0] if isinstance(locations[0], dict) else {}
        adresse = first.get("adresse") if isinstance(first.get("adresse"), dict) else first
        ort = adresse.get("ort") if isinstance(adresse, dict) else None
        if ort:
            region = adresse.get("region") if isinstance(adresse, dict) else None
            if region and str(region).lower() not in {str(ort).lower(), "deutschland"}:
                return f"{ort}, {str(region).replace('_', ' ').title()}"
            return str(ort)
    arbeitsort = payload.get("arbeitsort")
    if isinstance(arbeitsort, dict):
        return str(arbeitsort.get("ort") or "")
    if isinstance(arbeitsort, str):
        return arbeitsort
    return ""


def _nested_von(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        von = value.get("von")
        return str(von) if von else None
    return None


def _employment_type(payload: Dict[str, Any]) -> Optional[str]:
    if payload.get("arbeitszeitVollzeit") is True:
        return "Vollzeit"
    models = payload.get("arbeitszeitmodelle")
    if isinstance(models, list) and models:
        return str(models[0])
    if payload.get("arbeitszeit"):
        return str(payload.get("arbeitszeit"))
    return None
