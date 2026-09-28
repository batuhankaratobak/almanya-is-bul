"""HTTP client for the public Arbeitsagentur Jobsuche REST API."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

DEFAULT_BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
# Public client id documented by bundesAPI/jobsuche-api (not a private secret).
DEFAULT_API_KEY = "jobboerse-jobsuche"
DEFAULT_USER_AGENT = "GermanyJobHunter/0.1 (+local MVP; respectful fetch)"


class ArbeitsagenturClientError(RuntimeError):
    """Raised when the Jobsuche API request fails."""


class ArbeitsagenturClient:
    """Thin wrapper around the Jobsuche search + detail endpoints."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("ARBEITSAGENTUR_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "/"
        )
        self.api_key = api_key or os.getenv("ARBEITSAGENTUR_API_KEY") or DEFAULT_API_KEY
        self.timeout = float(timeout or os.getenv("ARBEITSAGENTUR_TIMEOUT") or 20)
        self.user_agent = user_agent or os.getenv("ARBEITSAGENTUR_USER_AGENT") or DEFAULT_USER_AGENT
        self._transport = transport
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                transport=self._transport,
                follow_redirects=True,
                headers={
                    "X-API-Key": self.api_key,
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
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
        size: int = 50,
        angebotsart: int = 1,
    ) -> Dict[str, Any]:
        """
        Search Germany-wide job listings.

        Nationwide strategy: omit `wo` / `umkreis` so results are not city-bound.
        """
        params = {
            "was": query,
            "angebotsart": angebotsart,
            "page": page,
            "size": size,
        }
        return self._get("/pc/v6/jobs", params=params)

    def fetch_job_details(self, referenznummer: str) -> Dict[str, Any]:
        encoded = base64.b64encode(referenznummer.encode("utf-8")).decode("ascii")
        # Path-safe: keep padding; API expects standard base64 path segment.
        return self._get(f"/pc/v4/jobdetails/{quote(encoded, safe='')}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._get_client().get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ArbeitsagenturClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise ArbeitsagenturClientError(f"Network error: {exc}") from exc

        if response.status_code >= 400:
            raise ArbeitsagenturClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ArbeitsagenturClientError("Malformed JSON response") from exc
        if not isinstance(payload, dict):
            raise ArbeitsagenturClientError("Unexpected response shape")
        return payload


def extract_search_results(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Support both v6 (`ergebnisliste`) and older (`stellenangebote`) shapes."""
    if isinstance(payload.get("ergebnisliste"), list):
        return [item for item in payload["ergebnisliste"] if isinstance(item, dict)]
    if isinstance(payload.get("stellenangebote"), list):
        return [item for item in payload["stellenangebote"] if isinstance(item, dict)]
    return []


def build_job_url(referenznummer: str) -> str:
    return f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{referenznummer}"
