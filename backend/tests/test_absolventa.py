"""Unit tests for Absolventa mapping/filters (no live network)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx

from app.sources.absolventa import AbsolventaSource, _looks_like_it_job_url
from app.sources.absolventa_client import AbsolventaClient, source_job_id_from_url
from app.sources.filters import is_germany_relevant, matches_target_role


FIXTURES = BACKEND_ROOT / "tests" / "fixtures"


def test_url_and_id_helpers() -> None:
    url = "https://www.absolventa.de/stellenangebote/10372861-s-werkstudent-it-systemadministration-m-w-d"
    assert _looks_like_it_job_url(url) is True
    assert _looks_like_it_job_url("https://www.absolventa.de/stellenangebote/1-s-koch-m-w-d") is False
    assert source_job_id_from_url(url) == "10372861"


def test_germany_and_role_filters() -> None:
    ok = {
        "title": "Junior Softwareentwickler",
        "location": "Berlin",
        "country": "DE",
        "description": "Software development tasks and requirements.",
    }
    assert is_germany_relevant(ok) is True
    assert matches_target_role(ok, ["Junior Softwareentwickler"], ["software_development"]) is True
    bad = {
        "title": "Koch",
        "location": "Berlin",
        "description": "Kitchen work",
    }
    assert matches_target_role(bad, ["Junior Softwareentwickler"], ["software_development"]) is False


def test_fetch_with_mock_transport() -> None:
    html = (FIXTURES / "absolventa_jobposting.html").read_text(encoding="utf-8")
    sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset>
      <loc>https://www.absolventa.de/stellenangebote/999001-s-junior-softwareentwickler-m-w-d</loc>
      <loc>https://www.absolventa.de/stellenangebote/999002-s-koch-m-w-d</loc>
    </urlset>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "sitemap" in url:
            return httpx.Response(200, text=sitemap, headers={"content-type": "application/xml"})
        if "999001" in url:
            return httpx.Response(200, text=html)
        return httpx.Response(404, text="missing")

    source = AbsolventaSource(
        client=AbsolventaClient(transport=httpx.MockTransport(handler)),
        max_jobs=10,
        max_candidate_urls=10,
        detail_concurrency=2,
    )
    jobs = source.fetch_jobs(["Junior Softwareentwickler"])
    assert len(jobs) == 1
    assert jobs[0].source == "Absolventa"
    assert jobs[0].company == "Absolventa Test GmbH"
    assert "Berlin" in jobs[0].location
    assert jobs[0].job_url.startswith("https://www.absolventa.de/")


def test_http_failure_raises() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    source = AbsolventaSource(
        client=AbsolventaClient(transport=httpx.MockTransport(handler)),
        max_jobs=5,
    )
    try:
        source.fetch_jobs(["Junior Softwareentwickler"])
        raise AssertionError("expected failure")
    except Exception as exc:
        assert "503" in str(exc) or "HTTP" in str(exc)


def run_all() -> None:
    tests = [
        test_url_and_id_helpers,
        test_germany_and_role_filters,
        test_fetch_with_mock_transport,
        test_http_failure_raises,
    ]
    for test in tests:
        test()
    print(f"Absolventa unit tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
