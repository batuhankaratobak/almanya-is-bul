"""HTTP client for the public EURES job-search JSON API."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

import httpx

DEFAULT_BASE_URL = "https://europa.eu/eures/api"
DEFAULT_USER_AGENT = "GermanyJobHunter/0.1 (+local MVP; respectful fetch)"


class EuresClientError(RuntimeError):
    """Raised when the EURES API request fails."""


class EuresClient:
    """
    Thin wrapper around the publicly reachable EURES search endpoints used by
    https://europa.eu/eures (no API key).
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("EURES_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout or os.getenv("EURES_TIMEOUT") or 20)
        self.user_agent = user_agent or os.getenv("EURES_USER_AGENT") or DEFAULT_USER_AGENT
        self._transport = transport
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                transport=self._transport,
                follow_redirects=True,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def search_jobs(
        self,
        query: str,
        *,
        page: int = 1,
        results_per_page: int = 10,
        location_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "resultsPerPage": results_per_page,
            "page": page,
            "sortSearch": "MOST_RECENT",
            "keywords": [{"keyword": query, "specificSearchCode": "EVERYWHERE"}],
            "publicationPeriod": None,
            "occupationUris": [],
            "skillUris": [],
            "requiredExperienceCodes": [],
            "positionScheduleCodes": [],
            "sectorCodes": [],
            "educationAndQualificationLevelCodes": [],
            "positionOfferingCodes": [],
            "locationCodes": location_codes or ["de"],
            "euresFlagCodes": [],
            "otherBenefitsCodes": [],
            "requiredLanguages": [],
            "minNumberPost": None,
            "sessionId": f"gjh-{uuid.uuid4().hex[:12]}",
            "requestLanguage": "en",
        }
        return self._post("/jv-searchengine/public/jv-search/search", payload)

    def fetch_job_details(self, job_id: str) -> Dict[str, Any]:
        return self._get(f"/jv-searchengine/public/jv/id/{job_id}")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._get_client().post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise EuresClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise EuresClientError(f"Network error: {exc}") from exc
        return self._parse(response)

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._get_client().get(url)
        except httpx.TimeoutException as exc:
            raise EuresClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise EuresClientError(f"Network error: {exc}") from exc
        return self._parse(response)

    def _parse(self, response: httpx.Response) -> Dict[str, Any]:
        if response.status_code >= 400:
            raise EuresClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise EuresClientError("Malformed JSON response") from exc
        if not isinstance(payload, dict):
            raise EuresClientError("Unexpected response shape")
        return payload


def extract_search_results(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("jvs")
    if not isinstance(rows, list):
        return []
    return [item for item in rows if isinstance(item, dict)]


def build_job_url(job_id: str) -> str:
    return f"https://europa.eu/eures/portal/jv-se/jv-details/{job_id}"
