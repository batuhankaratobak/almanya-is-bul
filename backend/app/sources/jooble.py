"""Jooble REST search API — cross-country. Requires JOOBLE_API_KEY."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.config.markets import MARKET_LOCATIONS, MARKETS, compact_queries_for_market
from app.services.incremental import update_cursor
from app.services.normalization import normalize_raw_job
from app.services.source_quota import can_request, record_requests
from app.sources.base import JobSource
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT = 120


class JoobleSource(JobSource):
    """
    POST https://jooble.org/api/{api_key}

    Body: keywords, location, page, ResultOnPage, searchMode=1 (date).
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        daily_limit: Optional[int] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("JOOBLE_API_KEY") or "").strip()
        self.max_jobs = max(
            1, int(max_jobs if max_jobs is not None else os.getenv("JOOBLE_MAX_JOBS") or 80)
        )
        self.timeout = float(timeout or os.getenv("JOOBLE_TIMEOUT") or 20)
        self.daily_limit = int(
            daily_limit
            if daily_limit is not None
            else os.getenv("JOOBLE_DAILY_LIMIT") or DEFAULT_DAILY_LIMIT
        )
        self._transport = transport
        markets_raw = (os.getenv("JOOBLE_MARKETS") or "DE").strip()
        selected = [m.strip().upper() for m in markets_raw.split(",") if m.strip()]
        self.markets = [m for m in selected if m in MARKET_LOCATIONS] or ["DE"]
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Jooble"

    @property
    def implemented(self) -> bool:
        return bool(self.api_key)

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        if not self.implemented:
            raise NotImplementedError(
                "Jooble requires JOOBLE_API_KEY "
                f"(received {len(search_terms)} search terms)"
            )

        collected: Dict[str, NormalizedJob] = {}
        raw_seen = 0
        url = f"https://jooble.org/api/{self.api_key}"
        markets = self.markets or list(MARKETS)

        with httpx.Client(
            timeout=self.timeout,
            transport=self._transport,
            headers={
                "User-Agent": "GermanyJobHunter/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        ) as client:
            for market in markets:
                if len(collected) >= self.max_jobs:
                    break
                location = MARKET_LOCATIONS[market]
                for keywords in compact_queries_for_market(market, max_terms=5):
                    if len(collected) >= self.max_jobs:
                        break
                    if not can_request(self.name, daily_limit=self.daily_limit):
                        logger.warning("Jooble daily quota reached (%s)", self.daily_limit)
                        break
                    body = {
                        "keywords": keywords,
                        "location": location,
                        "page": "1",
                        "ResultOnPage": "20",
                        "searchMode": "1",
                    }
                    try:
                        response = client.post(url, json=body)
                        record_requests(self.name, 1)
                        response.raise_for_status()
                        payload = response.json()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Jooble %s/%s failed: %s", market, keywords, exc)
                        continue

                    rows = payload.get("jobs") if isinstance(payload, dict) else []
                    if not isinstance(rows, list):
                        rows = []
                    raw_seen += len(rows)
                    for item in rows:
                        if not isinstance(item, dict):
                            continue
                        mapped = map_jooble_raw(item, market=market)
                        if not matches_target_role(mapped, search_terms, []):
                            continue
                        try:
                            job = normalize_raw_job(mapped, source=self.name)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Skipping Jooble job: %s", exc)
                            continue
                        key = job.source_job_id or job.job_url or f"{job.title}|{job.company}"
                        collected[key] = job

        self.last_raw_jobs = raw_seen
        jobs = list(collected.values())
        self.last_accepted_jobs = len(jobs)
        if jobs:
            newest = max((j.date_posted for j in jobs if j.date_posted), default=None)
            update_cursor(
                self.name,
                last_seen_at=newest,
                last_ids=[j.source_job_id or "" for j in jobs[:50]],
            )
        return jobs


def map_jooble_raw(item: Dict[str, Any], *, market: str) -> Dict[str, Any]:
    return {
        "source_job_id": str(item.get("id") or item.get("link") or ""),
        "title": item.get("title") or "",
        "company": item.get("company") or "",
        "location": item.get("location") or MARKET_LOCATIONS.get(market, market),
        "country": market,
        "description": item.get("snippet") or item.get("description") or "",
        "job_url": item.get("link") or "",
        "application_url": item.get("link") or "",
        "date_posted": item.get("updated") or item.get("date"),
        "employment_type": item.get("type"),
        "remote": "remote" in f"{item.get('title')} {item.get('location')}".casefold(),
    }
