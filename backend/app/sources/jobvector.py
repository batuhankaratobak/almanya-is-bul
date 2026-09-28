"""Jobvector source placeholder — no reliable public access without partner API."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class JobvectorSource(JobSource):
    """
    Not implemented.

    Reason: Jobvector's public site is protected by Cloudflare bot challenge
    (HTTP 403 "Just a moment..."). The documented Jobvector API is a partner/
    customer integration, not a free public job-read feed. Aggressive HTML
    scraping would require bypassing anti-bot protections, which we refuse.
    """

    @property
    def name(self) -> str:
        return "Jobvector"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            "(Jobvector: Cloudflare 403 / partner-only API; "
            f"{len(search_terms)} terms)"
        )
