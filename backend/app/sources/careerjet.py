"""Careerjet Affiliate API — cross-country. Requires CAREERJET_API_KEY."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.config.markets import CAREERJET_LOCALES, MARKETS, MARKET_LOCATIONS, compact_queries_for_market
from app.services.incremental import update_cursor
from app.services.normalization import normalize_raw_job
from app.services.source_quota import can_request, record_requests
from app.sources.base import JobSource
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

DEFAULT_DAILY_LIMIT = 120
API_URL = "https://public.api.careerjet.net/search"


class CareerjetSource(JobSource):
    """
    GET https://public.api.careerjet.net/search

    Requires affiliate key + user_ip + user_agent (vendor contract).
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        daily_limit: Optional[int] = None,
        user_ip: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.getenv("CAREERJET_API_KEY") or ""
        ).strip()
        self.max_jobs = max(
            1, int(max_jobs if max_jobs is not None else os.getenv("CAREERJET_MAX_JOBS") or 80)
        )
        self.timeout = float(timeout or os.getenv("CAREERJET_TIMEOUT") or 20)
        self.daily_limit = int(
            daily_limit
            if daily_limit is not None
            else os.getenv("CAREERJET_DAILY_LIMIT") or DEFAULT_DAILY_LIMIT
        )
        self.user_ip = (
            user_ip if user_ip is not None else os.getenv("CAREERJET_USER_IP") or "127.0.0.1"
        ).strip()
        self.user_agent = os.getenv("CAREERJET_USER_AGENT") or "GermanyJobHunter/1.0"
        self._transport = transport
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "Careerjet"

    @property
    def implemented(self) -> bool:
        return bool(self.api_key)

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        if not self.implemented:
            raise NotImplementedError(
                "Careerjet requires CAREERJET_API_KEY "
                f"(received {len(search_terms)} search terms)"
            )

        collected: Dict[str, NormalizedJob] = {}
        raw_seen = 0

        with httpx.Client(
            timeout=self.timeout,
            transport=self._transport,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        ) as client:
            for market in MARKETS:
                if len(collected) >= self.max_jobs:
                    break
                locales = CAREERJET_LOCALES.get(market) or ("en_GB",)
                locale = locales[0]
                location = MARKET_LOCATIONS[market]
                for keywords in compact_queries_for_market(market, max_terms=5):
                    if len(collected) >= self.max_jobs:
                        break
                    if not can_request(self.name, daily_limit=self.daily_limit):
                        logger.warning("Careerjet daily quota reached (%s)", self.daily_limit)
                        break
                    params = {
                        "affid": self.api_key,
                        "keywords": keywords,
                        "location": location,
                        "locale_code": locale,
                        "page": 1,
                        "pagesize": 20,
                        "sort": "date",
                        "user_ip": self.user_ip,
                        "user_agent": self.user_agent,
                    }
                    try:
                        response = client.get(API_URL, params=params)
                        record_requests(self.name, 1)
                        response.raise_for_status()
                        payload = response.json()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Careerjet %s/%s failed: %s", market, keywords, exc)
                        continue

                    rows = payload.get("jobs") if isinstance(payload, dict) else []
                    if not isinstance(rows, list):
                        rows = []
                    raw_seen += len(rows)
                    for item in rows:
                        if not isinstance(item, dict):
                            continue
                        mapped = map_careerjet_raw(item, market=market)
                        if not matches_target_role(mapped, search_terms, []):
                            continue
                        try:
                            job = normalize_raw_job(mapped, source=self.name)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Skipping Careerjet job: %s", exc)
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


def map_careerjet_raw(item: Dict[str, Any], *, market: str) -> Dict[str, Any]:
    return {
        "source_job_id": str(item.get("url") or item.get("title") or ""),
        "title": item.get("title") or "",
        "company": item.get("company") or "",
        "location": item.get("locations") or item.get("location") or MARKET_LOCATIONS.get(market, market),
        "country": market,
        "description": item.get("description") or "",
        "job_url": item.get("url") or "",
        "application_url": item.get("url") or "",
        "date_posted": item.get("date"),
        "employment_type": item.get("contracttype") or item.get("contractperiod"),
        "remote": "remote" in f"{item.get('title')} {item.get('description')}".casefold(),
    }
