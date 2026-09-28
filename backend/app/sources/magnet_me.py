"""Magnet.me — NL graduate/tech board stub (no public vacancy API)."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class MagnetMeSource(JobSource):
    """
    Not implemented as automated fetch.

    Reason: Magnet.me is account/JS oriented without a documented public
    vacancy API for personal tools. Manual deep-link fallback is provided.
    """

    @property
    def name(self) -> str:
        return "Magnet.me"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            f"(Magnet.me: no public vacancy API; {len(search_terms)} terms)"
        )
