"""Adzuna Jobs API — cross-country (DE/CH/FR/NL). Requires app_id + app_key."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config.markets import ADZUNA_COUNTRY_CODES, MARKETS, cross_country_refresh_plan
from app.services.incremental import get_last_seen_at, update_cursor
from app.services.normalization import normalize_raw_job
from app.services.source_quota import can_request, record_requests
from app.sources.base import JobSource
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT = 200  # keep headroom under Adzuna's default 250/day


class AdzunaSource(JobSource):
    """
    GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}

    Auth: app_id + app_key query params.
    Without credentials the source stays registered but not implemented.
    """

    def __init__(
        self,
        *,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        daily_limit: Optional[int] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.app_id = (app_id if app_id is not None else os.getenv("ADZUNA_APP_ID") or "").strip()
        self.app_key = (app_key if app_key is not None else os.getenv("ADZUNA_APP_KEY") or "").strip()
        self.max_jobs = max(
            1, int(max_jobs if max_jobs is not None else os.getenv("ADZUNA_MAX_JOBS") or 80)
        )
        self.timeout = float(timeout or os.getenv("ADZUNA_TIMEOUT") or 20)
        self.daily_limit = int(
            daily_limit
            if daily_limit is not None
            else os.getenv("ADZUNA_DAILY_LIMIT") or DEFAULT_DAILY_LIMIT
        )
        self._transport = transport
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Adzuna"

    @property
    def implemented(self) -> bool:
        return bool(self.app_id and self.app_key)

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        if not self.implemented:
            raise NotImplementedError(
                "Adzuna requires ADZUNA_APP_ID and ADZUNA_APP_KEY "
                f"(received {len(search_terms)} search terms)"
            )

        plan = cross_country_refresh_plan(MARKETS, max_terms=6, pages_per_query=1)
        # Prefer compact market plan over exploding search_terms.
        collected: Dict[str, NormalizedJob] = {}
        raw_seen = 0
        newest: Optional[datetime] = get_last_seen_at(self.name)
        cutoff = newest

        with httpx.Client(
            timeout=self.timeout,
            transport=self._transport,
            headers={"User-Agent": "GermanyJobHunter/1.0", "Accept": "application/json"},
        ) as client:
            for step in plan:
                if len(collected) >= self.max_jobs:
                    break
                if not can_request(self.name, daily_limit=self.daily_limit):
                    logger.warning("Adzuna daily quota reached (%s)", self.daily_limit)
                    break

                market = str(step["market"])
                country = ADZUNA_COUNTRY_CODES.get(market)
                if not country:
                    continue
                page = int(step["page"])
                keywords = str(step["keywords"])
                url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
                params = {
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "what": keywords,
                    "results_per_page": 20,
                    "sort_by": "date",
                    "content-type": "application/json",
                }
                try:
                    response = client.get(url, params=params)
                    record_requests(self.name, 1)
                    response.raise_for_status()
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Adzuna %s/%s failed: %s", market, keywords, exc)
                    continue

                rows = payload.get("results") if isinstance(payload, dict) else []
                if not isinstance(rows, list):
                    rows = []
                raw_seen += len(rows)

                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    mapped = map_adzuna_raw(item, market=market)
                    created = _parse_dt(mapped.get("date_posted"))
                    if cutoff and created and created <= cutoff:
                        continue
                    if not matches_target_role(mapped, search_terms, []):
                        continue
                    try:
                        job = normalize_raw_job(mapped, source=self.name)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Skipping Adzuna job: %s", exc)
                        continue
                    key = job.source_job_id or job.job_url or f"{job.title}|{job.company}"
                    collected[key] = job
                    if job.date_posted and (newest is None or job.date_posted > newest):
                        newest = job.date_posted
                    if len(collected) >= self.max_jobs:
                        break

        self.last_raw_jobs = raw_seen
        jobs = list(collected.values())
        self.last_accepted_jobs = len(jobs)
        if newest:
            update_cursor(self.name, last_seen_at=newest, last_ids=[j.source_job_id or "" for j in jobs[:50]])
        return jobs


def map_adzuna_raw(item: Dict[str, Any], *, market: str) -> Dict[str, Any]:
    location = ""
    loc = item.get("location")
    if isinstance(loc, dict):
        location = str(loc.get("display_name") or loc.get("area") or "")
        if isinstance(loc.get("area"), list):
            location = ", ".join(str(a) for a in loc["area"] if a)
    company = ""
    company_obj = item.get("company")
    if isinstance(company_obj, dict):
        company = str(company_obj.get("display_name") or "")
    return {
        "source_job_id": str(item.get("id") or ""),
        "title": item.get("title") or "",
        "company": company,
        "location": location,
        "country": market,
        "description": item.get("description") or "",
        "job_url": item.get("redirect_url") or "",
        "application_url": item.get("redirect_url") or "",
        "date_posted": item.get("created"),
        "employment_type": (
            item.get("contract_type") or item.get("contract_time")
        ),
        "remote": "remote" in f"{item.get('title')} {item.get('description')}".casefold(),
    }


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
