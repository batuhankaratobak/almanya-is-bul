"""Glassdoor Germany placeholder — no reliable public automated access."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class GlassdoorSource(JobSource):
    """
    Not implemented.

    Reason: Glassdoor job search endpoints return HTTP 403 for automated clients.
    There is no documented public job API/RSS for Glassdoor Germany. Circumventing
    anti-bot / access controls is out of scope.
    """

    @property
    def name(self) -> str:
        return "Glassdoor"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            f"(Glassdoor Germany returns 403 / no public job API; {len(search_terms)} terms)"
        )
