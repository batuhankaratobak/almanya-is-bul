"""Tests for the resilient multi-source manager."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.sources import (
    JobSource,
    NormalizedJob,
    SourceManager,
    create_default_source_manager,
)
from app.sources.germantechjobs import GermanTechJobsSource
from app.sources.jooble import JoobleSource


class SuccessSource(JobSource):
    def __init__(self, name: str, jobs: List[NormalizedJob]) -> None:
        self._name = name
        self._jobs = jobs

    @property
    def name(self) -> str:
        return self._name

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        assert search_terms  # ensure terms are forwarded
        return list(self._jobs)


class FailingSource(JobSource):
    def __init__(self, name: str, message: str = "timeout") -> None:
        self._name = name
        self._message = message

    @property
    def name(self) -> str:
        return self._name

    @property
    def implemented(self) -> bool:
        return True

    def fetch_jobs(self, search_terms: List[str]) -> List[NormalizedJob]:
        raise TimeoutError(self._message)


def test_multiple_sources_can_be_registered() -> None:
    manager = SourceManager()
    manager.register(SuccessSource("A", []))
    manager.register(SuccessSource("B", []))
    assert manager.registered_sources() == ["A", "B"]


def test_one_source_can_succeed() -> None:
    job = NormalizedJob(
        source="Arbeitsagentur",
        source_job_id="1",
        title="Junior Softwareentwickler",
        company="Example GmbH",
        location="Berlin",
    )
    manager = SourceManager()
    manager.register(SuccessSource("Arbeitsagentur", [job]))

    result = manager.fetch_all(["Junior Softwareentwickler"])

    assert len(result.jobs) == 1
    assert result.jobs[0].title == "Junior Softwareentwickler"
    stats = result.source_stats()
    assert stats["Arbeitsagentur"]["status"] == "success"
    assert stats["Arbeitsagentur"]["jobs_found"] == 1
    assert isinstance(stats["Arbeitsagentur"]["duration_seconds"], float)


def test_one_source_can_fail_without_stopping_others() -> None:
    ok_job = NormalizedJob(
        source="Arbeitnow",
        source_job_id="42",
        title="Junior Backend Developer",
        company="Tech AG",
        location="München",
    )
    manager = SourceManager()
    manager.register(FailingSource("Arbeitsagentur", "timeout"))
    manager.register(SuccessSource("Arbeitnow", [ok_job]))
    manager.register(FailingSource("GermanTechJobs", "connection refused"))

    result = manager.fetch_all(["Junior Backend Developer", "Junior Backend Entwickler"])

    assert len(result.jobs) == 1
    assert result.jobs[0].source == "Arbeitnow"

    stats = result.source_stats()
    assert stats["Arbeitsagentur"]["status"] == "failed"
    assert stats["Arbeitsagentur"]["error"] == "timeout"
    assert stats["Arbeitsagentur"]["jobs_found"] == 0

    assert stats["Arbeitnow"]["status"] == "success"
    assert stats["Arbeitnow"]["jobs_found"] == 1
    assert isinstance(stats["Arbeitnow"]["duration_seconds"], float)

    assert stats["GermanTechJobs"]["status"] == "failed"
    assert "connection refused" in str(stats["GermanTechJobs"]["error"])


def test_default_sources_registration_and_placeholder_status() -> None:
    manager = create_default_source_manager()
    assert manager.registered_sources() == [
        "Arbeitsagentur",
        "Arbeitnow",
        "Absolventa",
        "EURES",
        "Jobicy",
        "Remotive",
        "Jooble",
        "Make it in Germany",
        "Jobvector",
        "GermanTechJobs",
        "Glassdoor",
    ]
    sources = {source.name: source for source in manager.get_sources()}
    assert sources["Arbeitsagentur"].implemented is True
    assert sources["Arbeitnow"].implemented is True
    assert sources["Absolventa"].implemented is True
    assert sources["EURES"].implemented is True
    assert sources["Jobicy"].implemented is True
    assert sources["Remotive"].implemented is True
    assert "Jooble" in sources
    assert JoobleSource(api_key="").implemented is False
    assert sources["Jobvector"].implemented is False
    assert sources["Make it in Germany"].implemented is False
    assert sources["GermanTechJobs"].implemented is False
    assert sources["Glassdoor"].implemented is False

    # Avoid live network: only run remaining placeholders through manager.
    placeholder_manager = SourceManager()
    placeholder_manager.register(GermanTechJobsSource())
    result = placeholder_manager.fetch_all(["Junior Software Developer"])
    stats = result.source_stats()
    assert result.jobs == []
    assert stats["GermanTechJobs"]["status"] == "not_implemented"
    assert stats["GermanTechJobs"]["jobs_found"] == 0


def run_all() -> None:
    test_multiple_sources_can_be_registered()
    test_one_source_can_succeed()
    test_one_source_can_fail_without_stopping_others()
    test_default_sources_registration_and_placeholder_status()
    print("Source manager tests passed.")


if __name__ == "__main__":
    run_all()
