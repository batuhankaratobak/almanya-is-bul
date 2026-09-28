"""Unit tests for EURES mapping/filters (no live network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx

from app.sources.eures import EuresSource, map_eures_raw
from app.sources.eures_client import EuresClient, build_job_url


FIXTURES = BACKEND_ROOT / "tests" / "fixtures"


def test_map_eures_raw() -> None:
    payload = json.loads((FIXTURES / "eures_search.json").read_text(encoding="utf-8"))
    mapped = map_eures_raw(payload["jvs"][0])
    assert mapped["source_job_id"] == "MTAwMDEtVEVTVC0xLTE"
    assert mapped["company"] == "EURES Test GmbH"
    assert mapped["job_url"] == build_job_url("MTAwMDEtVEVTVC0xLTE")
    assert "Germany" in mapped["location"]


def test_fetch_filters_non_it_roles() -> None:
    payload = json.loads((FIXTURES / "eures_search.json").read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "jv-search" in str(request.url):
            return httpx.Response(200, json=payload)
        return httpx.Response(404, text="missing")

    source = EuresSource(
        client=EuresClient(transport=httpx.MockTransport(handler)),
        max_results_per_query=5,
        max_total_jobs=10,
        search_concurrency=2,
    )
    jobs = source.fetch_jobs(["Junior Software Developer"])
    assert len(jobs) == 1
    assert jobs[0].source == "EURES"
    assert jobs[0].title.startswith("Junior Software Developer")
    assert jobs[0].company == "EURES Test GmbH"


def test_http_failure_raises() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    source = EuresSource(
        client=EuresClient(transport=httpx.MockTransport(handler)),
        max_results_per_query=3,
        max_total_jobs=3,
    )
    try:
        source.fetch_jobs(["Software Engineer"])
        raise AssertionError("expected failure")
    except Exception as exc:
        assert "503" in str(exc) or "HTTP" in str(exc)


def run_all() -> None:
    tests = [
        test_map_eures_raw,
        test_fetch_filters_non_it_roles,
        test_http_failure_raises,
    ]
    for test in tests:
        test()
    print(f"EURES unit tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
