"""Common interface for job source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.sources.normalized_job import NormalizedJob


class JobSource(ABC):
    """Base class every job source must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable source identifier used in stats and storage."""

    @property
    def enabled(self) -> bool:
        """Whether this source is included in refresh runs."""
        return True

    @property
    def implemented(self) -> bool:
        """Whether live fetching is actually implemented."""
        return False

    @abstractmethod
    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        """Fetch jobs for the given German/English search terms."""
