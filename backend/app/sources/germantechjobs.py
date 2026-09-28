"""GermanTechJobs source placeholder — public API deprecated / unavailable."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class GermanTechJobsSource(JobSource):
    """
    Not implemented.

    Reason: `GET https://germantechjobs.de/api/jobs` now returns
    "ENDPOINT Deprecated - contact hello@swissdevjobs.ch". The site is a
    Cloudflare-fronted SPA without schema.org JobPosting JSON-LD or a
    documented public replacement feed. Third-party scrapers exist, but we do
    not bypass Cloudflare / anti-bot protections.
    """

    @property
    def name(self) -> str:
        return "GermanTechJobs"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            "(GermanTechJobs: /api/jobs deprecated; Cloudflare SPA; no public RSS; "
            f"{len(search_terms)} terms)"
        )
