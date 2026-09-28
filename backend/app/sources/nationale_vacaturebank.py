"""Nationale Vacaturebank — NL board stub until official feed/partner access."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class NationaleVacaturebankSource(JobSource):
    """
    Not implemented as automated fetch.

    Reason: Nationale Vacaturebank does not expose a documented public job API
    suitable for personal automation. Manual deep-link fallback is provided.
    """

    @property
    def name(self) -> str:
        return "Nationale Vacaturebank"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            f"(Nationale Vacaturebank: no public vacancy API; {len(search_terms)} terms)"
        )
