"""jobs.ch placeholder — no reliable public vacancy API for personal use."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class JobsChSource(JobSource):
    """
    Not implemented as automated fetch.

    Reason: jobs.ch does not publish a documented public job search API for
    personal tools. Aggressive HTML scraping would violate ToS / anti-bot
    controls. Use the manual deep-link panel instead until a partner feed exists.
    """

    @property
    def name(self) -> str:
        return "jobs.ch"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            f"(jobs.ch: no public vacancy API/RSS; {len(search_terms)} terms)"
        )
