"""Jobicy public remote-jobs API (no auth). Europe remote supplement."""

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

DEFAULT_URL = "https://jobicy.com/api/v2/remote-jobs"
_HTML_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    text = _HTML_RE.sub(" ", value or "")
    return re.sub(r"\s+", " ", text).strip()


class JobicySource(JobSource):
    """
    GET https://jobicy.com/api/v2/remote-jobs

    Public JSON. Poll at most about once per hour (vendor guidance).
    """

    def __init__(
        self,
        *,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.max_jobs = max(
            1, int(max_jobs if max_jobs is not None else os.getenv("JOBICY_MAX_JOBS") or 40)
        )
        self.timeout = float(timeout or os.getenv("JOBICY_TIMEOUT") or 20)
        self._transport = transport
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Jobicy"

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        params = {
            "count": min(100, max(self.max_jobs, 20)),
            "geo": "europe",
            "industry": "engineering",
        }
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
            raise RuntimeError(f"Jobicy request failed: {exc}") from exc

        rows = payload.get("jobs") if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            rows = []
        self.last_raw_jobs = len(rows)

        jobs: List[NormalizedJob] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            mapped = map_jobicy_raw(item)
            if not matches_target_role(mapped, search_terms, []):
                continue
            try:
                jobs.append(normalize_raw_job(mapped, source=self.name))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping Jobicy job: %s", exc)
            if len(jobs) >= self.max_jobs:
                break
        self.last_accepted_jobs = len(jobs)
        return jobs


def map_jobicy_raw(item: Dict[str, Any]) -> Dict[str, Any]:
    description = _strip_html(str(item.get("jobDescription") or item.get("jobExcerpt") or ""))
    geo = str(item.get("jobGeo") or "Europe")
    return {
        "source_job_id": str(item.get("id") or item.get("jobSlug") or ""),
        "title": item.get("jobTitle") or "",
        "company": item.get("companyName") or "",
        "location": geo,
        "country": "EU",
        "description": description,
        "job_url": item.get("url") or "",
        "application_url": item.get("url") or "",
        "date_posted": item.get("pubDate"),
        "employment_type": (
            item.get("jobType")[0]
            if isinstance(item.get("jobType"), list) and item.get("jobType")
            else item.get("jobType")
        ),
        "remote": True,
        "tags": item.get("jobIndustry") if isinstance(item.get("jobIndustry"), list) else [],
    }
