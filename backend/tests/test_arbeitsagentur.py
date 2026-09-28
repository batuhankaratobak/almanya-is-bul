"""Unit tests for Arbeitsagentur mapping and source (no live network)."""

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
from app.services.deduplication import upsert_normalized_job
from app.services.refresh import refresh_jobs
from app.sources import SourceManager
from app.sources.arbeitsagentur import ArbeitsagenturSource, map_arbeitsagentur_raw
from app.sources.arbeitsagentur_client import ArbeitsagenturClient, build_job_url, extract_search_results
from app.sources.base import JobSource

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_extract_and_map_search_results() -> None:
    payload = _load("arbeitsagentur_search.json")
    results = extract_search_results(payload)
    assert len(results) == 2

    mapped = map_arbeitsagentur_raw(results[0], detail=None)
    assert mapped["referenznummer"] == "12265-TEST-1-S"
    assert mapped["titel"] == "Junior Softwareentwickler (m/w/d)"
    assert mapped["arbeitgeber"] == "Beispiel GmbH"
    assert mapped["arbeitsort"].startswith("Berlin")
    assert mapped["externeUrl"] == build_job_url("12265-TEST-1-S")
    # Search hits often omit full text; mapper keeps taxonomy signals from title/Beruf.
    assert "Junior Softwareentwickler" in mapped["stellenbeschreibung"]


def test_map_with_detail_and_missing_fields() -> None:
    search = _load("arbeitsagentur_search.json")["ergebnisliste"][0]
    detail = _load("arbeitsagentur_detail.json")
    mapped = map_arbeitsagentur_raw(search, detail=detail)
    assert "Wir suchen Verstärkung" in mapped["stellenbeschreibung"]
    assert mapped["arbeitszeit"] == "Vollzeit"

    empty = map_arbeitsagentur_raw({})
    assert empty["referenznummer"] is None
    assert empty["titel"] == ""
    assert empty["externeUrl"] == ""


def test_invalid_search_payload_returns_empty_list() -> None:
    assert extract_search_results({}) == []
    assert extract_search_results({"ergebnisliste": "bad"}) == []


def test_source_fetch_with_mock_transport_normalizes_and_scores() -> None:
    import base64
    from urllib.parse import unquote

    search = _load("arbeitsagentur_search.json")
    detail = _load("arbeitsagentur_detail.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if "/pc/v6/jobs" in str(request.url):
            return httpx.Response(200, json=search)
        if "/pc/v4/jobdetails/" in str(request.url):
            encoded = unquote(str(request.url).rstrip("/").split("/")[-1])
            ref = base64.b64decode(encoded).decode("utf-8")
            if ref == "12265-TEST-1-S":
                return httpx.Response(200, json=detail)
            return httpx.Response(404, text="not found")
        return httpx.Response(404, json={"error": "missing"})

    client = ArbeitsagenturClient(transport=httpx.MockTransport(handler))
    source = ArbeitsagenturSource(
        client=client,
        max_results_per_query=10,
        max_total_jobs=10,
        fetch_details=True,
    )
    assert source.implemented is True

    jobs = source.fetch_jobs(["Junior Softwareentwickler"])
    assert len(jobs) == 2
    assert all(job.source == "Arbeitsagentur" for job in jobs)
    first = next(job for job in jobs if job.source_job_id == "12265-TEST-1-S")
    assert first.company == "Beispiel GmbH"
    assert first.job_url.endswith("12265-TEST-1-S")
    assert "Wir suchen Verstärkung" in first.description
    assert first.match_score > 0
    assert first.match_category is not None


def test_source_manager_pipeline_with_mock_and_dedupe() -> None:
    import base64
    from urllib.parse import unquote

    search = _load("arbeitsagentur_search.json")
    detail = _load("arbeitsagentur_detail.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if "/pc/v6/jobs" in str(request.url):
            return httpx.Response(200, json=search)
        if "/pc/v4/jobdetails/" in str(request.url):
            encoded = unquote(str(request.url).rstrip("/").split("/")[-1])
            ref = base64.b64decode(encoded).decode("utf-8")
            if ref == "12265-TEST-1-S":
                return httpx.Response(200, json=detail)
            return httpx.Response(404, text="not found")
        return httpx.Response(500, text="boom")

    class PlaceholderArbeitnow(JobSource):
        @property
        def name(self) -> str:
            return "Arbeitnow"

        def fetch_jobs(self, search_terms):
            raise NotImplementedError("placeholder")

    client = ArbeitsagenturClient(transport=httpx.MockTransport(handler))
    manager = SourceManager()
    manager.register(
        ArbeitsagenturSource(
            client=client,
            max_results_per_query=5,
            max_total_jobs=5,
            fetch_details=True,
        )
    )
    manager.register(PlaceholderArbeitnow())

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    result = refresh_jobs(
        db,
        manager=manager,
        search_terms=["Junior Softwareentwickler"],
    )
    assert result.status == "completed"
    assert result.jobs_scanned == 2
    assert result.new_jobs == 2
    assert result.sources["Arbeitsagentur"].status == "success"
    assert result.sources["Arbeitsagentur"].jobs_found == 2
    assert result.sources["Arbeitnow"].status == "not_implemented"

    jobs = list(db.scalars(select(Job)).all())
    assert len(jobs) == 2
    jobs[0].status = "applied"
    db.commit()

    second = refresh_jobs(
        db,
        manager=manager,
        search_terms=["Junior Softwareentwickler"],
    )
    assert second.jobs_scanned == 2
    assert second.new_jobs == 0
    assert second.duplicates + second.updated_jobs >= 1
    preserved = db.scalar(select(Job).where(Job.source_job_id == "12265-TEST-1-S"))
    assert preserved is not None
    assert preserved.status == "applied"


def test_http_error_fails_source_cleanly() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = ArbeitsagenturClient(transport=httpx.MockTransport(handler))
    source = ArbeitsagenturSource(client=client, fetch_details=False)
    manager = SourceManager()
    manager.register(source)
    result = manager.fetch_all(["Junior Softwareentwickler"])
    assert result.jobs == []
    assert result.sources["Arbeitsagentur"].status == "failed"
    assert "HTTP 503" in str(result.sources["Arbeitsagentur"].error)


def run_all() -> None:
    tests = [
        test_extract_and_map_search_results,
        test_map_with_detail_and_missing_fields,
        test_invalid_search_payload_returns_empty_list,
        test_source_fetch_with_mock_transport_normalizes_and_scores,
        test_source_manager_pipeline_with_mock_and_dedupe,
        test_http_error_fails_source_cleanly,
    ]
    for test in tests:
        test()
    print(f"Arbeitsagentur unit tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
