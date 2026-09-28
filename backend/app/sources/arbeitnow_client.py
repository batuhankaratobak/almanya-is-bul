"""HTTP client for the public Arbeitnow job-board API."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

DEFAULT_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"
DEFAULT_USER_AGENT = "GermanyJobHunter/0.1 (+local MVP; respectful fetch)"


class ArbeitnowClientError(RuntimeError):
    """Raised when the Arbeitnow API request fails."""


class ArbeitnowClient:
    """Thin wrapper around GET /api/job-board-api?page=N."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("ARBEITNOW_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "?"
        )
        self.timeout = float(timeout or os.getenv("ARBEITNOW_TIMEOUT") or 20)
        self.user_agent = user_agent or os.getenv("ARBEITNOW_USER_AGENT") or DEFAULT_USER_AGENT
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
                },
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def fetch_page(self, page: int = 1) -> Dict[str, Any]:
        if page < 1:
            page = 1
        try:
            response = self._get_client().get(self.base_url, params={"page": page})
        except httpx.TimeoutException as exc:
            raise ArbeitnowClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise ArbeitnowClientError(f"Network error: {exc}") from exc

        if response.status_code >= 400:
            raise ArbeitnowClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ArbeitnowClientError("Malformed JSON response") from exc
        if not isinstance(payload, dict):
            raise ArbeitnowClientError("Unexpected response shape")
        return payload


def extract_jobs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def has_next_page(payload: Dict[str, Any], current_page: int) -> bool:
    links = payload.get("links")
    if isinstance(links, dict) and links.get("next"):
        return True
    meta = payload.get("meta")
    if isinstance(meta, dict):
        # Some responses omit last; stop when page returns empty.
        pass
    return False
