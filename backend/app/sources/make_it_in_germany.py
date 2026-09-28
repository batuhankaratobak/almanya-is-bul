"""Make it in Germany source placeholder — no independent public job API."""

from __future__ import annotations

from typing import List

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob


class MakeItInGermanySource(JobSource):
    """
    Not implemented as a separate live source.

    Reason: Make it in Germany job listings are supplied by the Bundesagentur
    für Arbeit Jobsuche (employers opt-in when posting). There is no independent
    public MIIG job API/RSS. Those Germany jobs are already covered by the
    Arbeitsagentur source; inventing a second scrape of the MIIG HTML portal
    would only duplicate BA data without a reliable structured endpoint.
    """

    @property
    def name(self) -> str:
        return "Make it in Germany"

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise NotImplementedError(
            "Reliable public automated access unavailable "
            "(Make it in Germany: no independent job API/RSS; listings are a "
            f"Bundesagentur für Arbeit channel — use Arbeitsagentur; {len(search_terms)} terms)"
        )
