"""Unit tests for Arbeitnow mapping/filters (no live network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Job
import app.models.job  # noqa: F401
import app.models.job_source_reference  # noqa: F401
from app.services.deduplication import list_source_links, upsert_normalized_job
from app.services.refresh import refresh_jobs
from app.sources import SourceManager
from app.sources.arbeitnow import (
    ArbeitnowSource,
    is_germany_relevant,
    map_arbeitnow_raw,
    matches_target_role,
)
from app.sources.arbeitnow_client import ArbeitnowClient, extract_jobs
from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_map_and_missing_fields() -> None:
    item = _load("arbeitnow_page1.json")["data"][0]
    mapped = map_arbeitnow_raw(item)
    assert mapped["slug"] == "junior-software-engineer-acme-berlin-1"
    assert mapped["company_name"] == "Acme GmbH"
    assert mapped["remote"] is False
    assert mapped["url"].startswith("https://")

    empty = map_arbeitnow_raw({})
    assert empty["title"] == ""
    assert empty["company_name"] == ""
    assert empty["url"] == ""


def test_germany_filtering() -> None:
    assert is_germany_relevant({"location": "Berlin, Germany", "title": "Dev", "slug": "x"})
    assert is_germany_relevant({"location": "DE Remote", "title": "IT Support", "slug": "y"})
    assert is_germany_relevant({"location": "Munich", "title": "Engineer", "slug": "z"})
    assert not is_germany_relevant(
        {"location": "London, United Kingdom", "title": "Nurse", "slug": "nurse-london"}
    )
    assert not is_germany_relevant(
        {"location": "Paris, France", "title": "Chef", "slug": "chef-paris"}
    )


def test_target_role_filtering() -> None:
    terms = ["Junior Software Engineer", "IT Support Specialist", "Junior QA Engineer"]
    cats = (
        "software_development",
        "it_support",
        "cybersecurity",
        "qa_testing",
        "system_administration",
        "application_support",
        "it_consulting",
    )
    keep = {
        "title": "Junior Software Engineer",
        "description": "Build APIs",
        "location": "Berlin, Germany",
    }
    drop = {
        "title": "Warehouse Worker",
        "description": "Pack boxes",
        "location": "Berlin, Germany",
    }
    assert matches_target_role(keep, terms, cats)
    assert not matches_target_role(drop, terms, cats)


def test_pagination_and_filters_with_mock_transport() -> None:
    page1 = _load("arbeitnow_page1.json")
    page2 = _load("arbeitnow_page2.json")

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page", "1")
        if page == "1":
            return httpx.Response(200, json=page1)
        if page == "2":
            return httpx.Response(200, json=page2)
        return httpx.Response(200, json={"data": [], "links": {"next": None}})

    source = ArbeitnowSource(
        client=ArbeitnowClient(transport=httpx.MockTransport(handler)),
        max_pages=2,
        max_jobs=50,
    )
    assert source.implemented is True
    jobs = source.fetch_jobs(
        ["Junior Software Engineer", "IT Support Specialist", "Junior QA Engineer"]
    )
    titles = {job.title for job in jobs}
    assert "Junior Software Engineer" in titles
    assert "IT Support Specialist" in titles
    assert "Junior QA Engineer" in titles
    assert "Warehouse Worker" not in titles
    assert "Nurse" not in titles
    assert all(job.source == "Arbeitnow" for job in jobs)
    assert all(job.job_url for job in jobs)


def test_source_failure_is_isolated() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    manager = SourceManager()
    manager.register(
        ArbeitnowSource(client=ArbeitnowClient(transport=httpx.MockTransport(handler)))
    )

    class OkSource(JobSource):
        @property
        def name(self) -> str:
            return "Arbeitsagentur"

        @property
        def implemented(self) -> bool:
            return True

        def fetch_jobs(self, search_terms):
            return [
                NormalizedJob(
                    source="Arbeitsagentur",
                    source_job_id="aa-1",
                    title="Junior Softwareentwickler",
                    company="AA GmbH",
                    location="Berlin",
                    job_url="https://example.com/aa-1",
                )
            ]

    manager.register(OkSource())
    result = manager.fetch_all(["Junior Software Engineer"])
    stats = result.source_stats()
    assert stats["Arbeitnow"]["status"] == "failed"
    assert stats["Arbeitsagentur"]["status"] == "success"
    assert len(result.jobs) == 1


def test_cross_source_duplicate_preserves_status_and_references() -> None:
    page1 = _load("arbeitnow_page1.json")
    # Force Arbeitnow job to match AA fingerprint.
    page1["data"][0]["title"] = "Junior Software Engineer"
    page1["data"][0]["company_name"] = "Acme GmbH"
    page1["data"][0]["location"] = "Berlin"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={**page1, "links": {"next": None}})

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    aa_job = NormalizedJob(
        source="Arbeitsagentur",
        source_job_id="aa-acme-1",
        title="Junior Software Engineer",
        company="Acme GmbH",
        location="Berlin",
        description="Original AA description",
        job_url="https://www.arbeitsagentur.de/jobsuche/jobdetail/aa-acme-1",
        match_score=80,
        match_category="Gut passend",
        status="applied",
    )
    first = upsert_normalized_job(db, aa_job)
    stored = db.get(Job, first.job_id)
    assert stored is not None
    stored.status = "applied"
    db.commit()

    class AASource(JobSource):
        @property
        def name(self) -> str:
            return "Arbeitsagentur"

        @property
        def implemented(self) -> bool:
            return True

        def fetch_jobs(self, search_terms):
            return [aa_job]

    manager = SourceManager()
    manager.register(AASource())
    manager.register(
        ArbeitnowSource(
            client=ArbeitnowClient(transport=httpx.MockTransport(handler)),
            max_pages=1,
        )
    )

    result = refresh_jobs(
        db,
        manager=manager,
        search_terms=["Junior Software Engineer", "IT Support Specialist"],
    )
    jobs = list(db.scalars(select(Job)).all())
    merged = db.scalar(select(Job).where(Job.source_job_id == "aa-acme-1"))
    assert merged is not None
    assert merged.status == "applied"
    links = list_source_links(db, merged)
    sources = {link["source"] for link in links}
    assert "Arbeitsagentur" in sources
    assert "Arbeitnow" in sources
    assert result.sources["Arbeitnow"].status == "success"
    # Other Arbeitnow IT jobs may still be inserted as new rows.
    assert len(jobs) >= 1
    assert result.duplicates + result.updated_jobs + result.new_jobs >= 1


def test_empty_page_and_invalid_payload() -> None:
    assert extract_jobs({}) == []
    assert extract_jobs({"data": "bad"}) == []

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [], "links": {"next": None}})

    source = ArbeitnowSource(
        client=ArbeitnowClient(transport=httpx.MockTransport(handler)),
        max_pages=2,
    )
    assert source.fetch_jobs(["Junior Software Engineer"]) == []


def run_all() -> None:
    tests = [
        test_map_and_missing_fields,
        test_germany_filtering,
        test_target_role_filtering,
        test_pagination_and_filters_with_mock_transport,
        test_source_failure_is_isolated,
        test_cross_source_duplicate_preserves_status_and_references,
        test_empty_page_and_invalid_payload,
    ]
    for test in tests:
        test()
    print(f"Arbeitnow unit tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
