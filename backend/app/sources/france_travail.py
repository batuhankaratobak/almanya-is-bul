"""France Travail (Pôle Emploi) Offres d'emploi API — requires OAuth client."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.config.markets import compact_queries_for_market
from app.services.incremental import update_cursor
from app.services.normalization import normalize_raw_job
from app.services.source_quota import can_request, record_requests
from app.sources.base import JobSource
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
DEFAULT_DAILY_LIMIT = 200


class FranceTravailSource(JobSource):
    """
    Official French employment agency vacancy API.

    Needs FRANCE_TRAVAIL_CLIENT_ID + FRANCE_TRAVAIL_CLIENT_SECRET
    (and optionally FRANCE_TRAVAIL_SCOPE).
    """

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        max_jobs: Optional[int] = None,
        timeout: Optional[float] = None,
        daily_limit: Optional[int] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.client_id = (
            client_id if client_id is not None else os.getenv("FRANCE_TRAVAIL_CLIENT_ID") or ""
        ).strip()
        self.client_secret = (
            client_secret
            if client_secret is not None
            else os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
            or ""
        ).strip()
        self.scope = (
            os.getenv("FRANCE_TRAVAIL_SCOPE")
            or "api_offresdemploiv2 o2dsoffre"
        ).strip()
        self.max_jobs = max(
            1,
            int(max_jobs if max_jobs is not None else os.getenv("FRANCE_TRAVAIL_MAX_JOBS") or 80),
        )
        self.timeout = float(timeout or os.getenv("FRANCE_TRAVAIL_TIMEOUT") or 25)
        self.daily_limit = int(
            daily_limit
            if daily_limit is not None
            else os.getenv("FRANCE_TRAVAIL_DAILY_LIMIT") or DEFAULT_DAILY_LIMIT
        )
        self._transport = transport
        self._token: Optional[str] = None
        self.last_raw_jobs = 0
        self.last_accepted_jobs = 0

    @property
    def name(self) -> str:
        return "France Travail"

    @property
    def implemented(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        if not self.implemented:
            raise NotImplementedError(
                "France Travail requires FRANCE_TRAVAIL_CLIENT_ID and "
                f"FRANCE_TRAVAIL_CLIENT_SECRET (received {len(search_terms)} terms)"
            )

        token = self._get_token()
        collected: Dict[str, NormalizedJob] = {}
        raw_seen = 0

        with httpx.Client(
            timeout=self.timeout,
            transport=self._transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "GermanyJobHunter/1.0",
            },
        ) as client:
            for keywords in compact_queries_for_market("FR", max_terms=6):
                if len(collected) >= self.max_jobs:
                    break
                if not can_request(self.name, daily_limit=self.daily_limit):
                    break
                params = {
                    "motsCles": keywords,
                    "range": "0-49",
                    "sort": "1",  # relevance/date oriented
                }
                try:
                    response = client.get(SEARCH_URL, params=params)
                    record_requests(self.name, 1)
                    if response.status_code == 204:
                        continue
                    response.raise_for_status()
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("France Travail '%s' failed: %s", keywords, exc)
                    continue

                rows = payload.get("resultats") if isinstance(payload, dict) else []
                if not isinstance(rows, list):
                    rows = []
                raw_seen += len(rows)
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    mapped = map_france_travail_raw(item)
                    if not matches_target_role(mapped, search_terms, []):
                        continue
                    try:
                        job = normalize_raw_job(mapped, source=self.name)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Skipping France Travail job: %s", exc)
                        continue
                    key = job.source_job_id or job.job_url
                    collected[key] = job

        self.last_raw_jobs = raw_seen
        jobs = list(collected.values())
        self.last_accepted_jobs = len(jobs)
        if jobs:
            newest = max((j.date_posted for j in jobs if j.date_posted), default=None)
            update_cursor(self.name, last_seen_at=newest)
        return jobs

    def _get_token(self) -> str:
        if self._token:
            return self._token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        with httpx.Client(
            timeout=self.timeout,
            transport=self._transport,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as client:
            # realm path commonly required by FT OAuth
            response = client.post(
                f"{TOKEN_URL}?realm=%2Fpartenaire",
                data=data,
            )
            response.raise_for_status()
            payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("France Travail OAuth did not return access_token")
        self._token = str(token)
        return self._token


def map_france_travail_raw(item: Dict[str, Any]) -> Dict[str, Any]:
    lieu = item.get("lieuTravail") if isinstance(item.get("lieuTravail"), dict) else {}
    entreprise = item.get("entreprise") if isinstance(item.get("entreprise"), dict) else {}
    contact = item.get("contact") if isinstance(item.get("contact"), dict) else {}
    job_url = (
        item.get("origineOffre", {}).get("urlOrigine")
        if isinstance(item.get("origineOffre"), dict)
        else None
    ) or contact.get("urlPostulation") or ""
    if not job_url and item.get("id"):
        job_url = f"https://candidat.francetravail.fr/offres/recherche/detail/{item['id']}"
    return {
        "source_job_id": str(item.get("id") or ""),
        "title": item.get("intitule") or "",
        "company": entreprise.get("nom") or "",
        "location": lieu.get("libelle") or "",
        "country": "FR",
        "description": item.get("description") or "",
        "job_url": job_url,
        "application_url": contact.get("urlPostulation") or job_url,
        "date_posted": item.get("dateCreation") or item.get("dateActualisation"),
        "employment_type": (
            item.get("typeContratLibelle") or item.get("typeContrat")
        ),
        "remote": str(item.get("nombrePostes") or "") == ""
        and "télétravail" in str(item.get("description") or "").casefold(),
    }
