"""SwissDevJobs placeholder — former public JSON endpoint is deprecated."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class SwissDevJobsSource(JobSource):
    """
    Not implemented as automated fetch.

    Reason: swissdevjobs.ch/api/jobs now returns
    "ENDPOINT Deprecated - contact hello@swissdevjobs.ch".
    No replacement public feed is documented. Use manual deep-links.
    """

    @property
    def name(self) -> str:
        return "SwissDevJobs"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            "(SwissDevJobs: public JSON endpoint deprecated; "
            f"{len(search_terms)} terms)"
        )
