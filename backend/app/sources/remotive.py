"""Remotive public remote-jobs API (no auth). Europe/global remote supplement."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from app.services.normalization import normalize_raw_job
from app.sources.base import JobSource
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

DEFAULT_URL = "https://remotive.com/api/remote-jobs"
_HTML_RE = re.compile(r"<[^>]+>")

_TARGET_MARKETS = ("germany", "switzerland", "france", "netherlands", "europe", "worldwide", "anywhere")


def _strip_html(value: str) -> str:
    text = _HTML_RE.sub(" ", value or "")
    return re.sub(r"\s+", " ", text).strip()


class RemotiveSource(JobSource):
    """GET https://remotive.com/api/remote-jobs — public JSON, no key."""

    def __init__(
        self,
        *,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.max_jobs = max(
            1, int(max_jobs if max_jobs is not None else os.getenv("REMOTIVE_MAX_JOBS") or 40)
        )
        self.timeout = float(timeout or os.getenv("REMOTIVE_TIMEOUT") or 20)
        self._transport = transport
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Remotive"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        params = {"category": "software-dev"}
        try:
            with httpx.Client(
                timeout=self.timeout,
                transport=self._transport,
                headers={"User-Agent": "GermanyJobHunter/1.0", "Accept": "application/json"},
            ) as client:
                response = client.get(DEFAULT_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Remotive request failed: {exc}") from exc

        rows = payload.get("jobs") if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            rows = []
        self.last_raw_jobs = len(rows)

        jobs: List[NormalizedJob] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            if not _is_relevant_remote(item):
                continue
            mapped = map_remotive_raw(item)
            if not matches_target_role(mapped, search_terms, []):
                continue
            try:
                jobs.append(normalize_raw_job(mapped, source=self.name))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping Remotive job: %s", exc)
            if len(jobs) >= self.max_jobs:
                break
        self.last_accepted_jobs = len(jobs)
        return jobs


def _is_relevant_remote(item: Dict[str, Any]) -> bool:
    candidate = " ".join(
        str(item.get(k) or "")
        for k in ("candidate_required_location", "job_type", "title", "company_name")
    ).casefold()
    if any(m in candidate for m in _TARGET_MARKETS):
        return True
    # Keep empty / worldwide-style locations for software-dev remote feed.
    loc = str(item.get("candidate_required_location") or "").strip()
    return not loc or loc.casefold() in {"worldwide", "anywhere", "remote", "europe"}


def map_remotive_raw(item: Dict[str, Any]) -> Dict[str, Any]:
    loc = str(item.get("candidate_required_location") or "Remote")
    country = "EU"
    low = loc.casefold()
    if "germany" in low or "deutschland" in low:
        country = "DE"
    elif "switzerland" in low or "schweiz" in low:
        country = "CH"
    elif "france" in low:
        country = "FR"
    elif "netherlands" in low or "holland" in low:
        country = "NL"
    return {
        "source_job_id": str(item.get("id") or item.get("url") or ""),
        "title": item.get("title") or "",
        "company": item.get("company_name") or "",
        "location": loc,
        "country": country,
        "description": _strip_html(str(item.get("description") or "")),
        "job_url": item.get("url") or "",
        "application_url": item.get("url") or "",
        "date_posted": item.get("publication_date"),
        "employment_type": item.get("job_type"),
        "remote": True,
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
    }
