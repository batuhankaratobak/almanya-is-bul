"""HTTP helpers for Absolventa public sitemap + JobPosting JSON-LD."""

from __future__ import annotations

import json
import os
import re
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

DEFAULT_SITEMAP_URL = "https://www.absolventa.de/sitemap-stellen.xml"
DEFAULT_USER_AGENT = "GermanyJobHunter/0.1 (+local MVP; respectful fetch)"
_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


class AbsolventaClientError(RuntimeError):
    """Raised when Absolventa public fetch fails."""


class AbsolventaClient:
    def __init__(
        self,
        *,
        sitemap_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.sitemap_url = sitemap_url or os.getenv("ABSOLVENTA_SITEMAP_URL") or DEFAULT_SITEMAP_URL
        self.timeout = float(timeout or os.getenv("ABSOLVENTA_TIMEOUT") or 20)
        self.user_agent = user_agent or os.getenv("ABSOLVENTA_USER_AGENT") or DEFAULT_USER_AGENT
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
                    "Accept": "application/xml,text/html,application/json,*/*",
                },
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def fetch_sitemap_urls(self) -> List[str]:
        try:
            response = self._get_client().get(self.sitemap_url)
        except httpx.TimeoutException as exc:
            raise AbsolventaClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise AbsolventaClientError(f"Network error: {exc}") from exc
        if response.status_code >= 400:
            raise AbsolventaClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        return re.findall(r"<loc>\s*(https?://[^<]+?)\s*</loc>", response.text)

    def fetch_job_posting(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            response = self._get_client().get(url)
        except httpx.TimeoutException as exc:
            raise AbsolventaClientError("Request timed out") from exc
        except httpx.HTTPError as exc:
            raise AbsolventaClientError(f"Network error: {exc}") from exc
        if response.status_code >= 400:
            raise AbsolventaClientError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        for block in _LD_RE.findall(response.text):
            try:
                payload = json.loads(unescape(block))
            except ValueError:
                continue
            candidates = payload if isinstance(payload, list) else [payload]
            for item in candidates:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        return None


def source_job_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    match = re.match(r"^(\d+)", slug)
    return match.group(1) if match else slug


def location_from_job_posting(posting: Dict[str, Any]) -> str:
    locations = posting.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list) or not locations:
        return ""
    first = locations[0] if isinstance(locations[0], dict) else {}
    address = first.get("address") if isinstance(first.get("address"), dict) else {}
    city = address.get("addressLocality") or first.get("name") or ""
    region = address.get("addressRegion") or ""
    if city and region and str(region).upper() not in {"DE", "DEUTSCHLAND", str(city).upper()}:
        return f"{city}, {region}"
    return str(city or "")


def country_from_job_posting(posting: Dict[str, Any]) -> str:
    locations = posting.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list) or not locations:
        return ""
    first = locations[0] if isinstance(locations[0], dict) else {}
    address = first.get("address") if isinstance(first.get("address"), dict) else {}
    return str(address.get("addressCountry") or address.get("addressRegion") or "")
