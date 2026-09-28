"""Welcome to the Jungle — structured HTML/API not reliably public; honest stub."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class WelcomeToTheJungleSource(JobSource):
    """
    Not implemented as automated fetch.

    Reason: WTTJ job search is JS-heavy / partner-gated. No stable documented
    public vacancy API for personal tools. Use manual deep-links until a feed
    or partner access exists.
    """

    @property
    def name(self) -> str:
        return "Welcome to the Jungle"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            f"(Welcome to the Jungle: no public vacancy API; {len(search_terms)} terms)"
        )
