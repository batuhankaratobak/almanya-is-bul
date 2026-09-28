"""Unit tests for cross-country API mappers, quota, and manual portals."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.markets import cross_country_refresh_plan, get_markets
from app.services import source_quota
from app.services.manual_portals import build_manual_portal_links
from app.sources.adzuna import AdzunaSource, map_adzuna_raw
from app.sources.careerjet import CareerjetSource, map_careerjet_raw
from app.sources.jobicy import JobicySource, map_jobicy_raw
from app.sources.jooble import JoobleSource, map_jooble_raw
from app.sources.remotive import map_remotive_raw


def test_markets_and_refresh_plan_are_compact() -> None:
    assert get_markets() == ["DE", "CH", "FR", "NL"]
    plan = cross_country_refresh_plan(max_terms=3, pages_per_query=1)
    assert len(plan) == 4 * 3
    assert all("market" in step and "keywords" in step for step in plan)


def test_jobicy_mapper_and_mock_fetch() -> None:
    mapped = map_jobicy_raw(
        {
            "id": 11,
            "jobTitle": "Junior Software Developer",
            "companyName": "Acme",
            "jobGeo": "Germany",
            "url": "https://example.com/jobs/11",
            "jobDescription": "<p>Python and SQL</p>",
            "jobType": ["Full-Time"],
            "jobIndustry": ["Engineering"],
            "pubDate": "2026-08-01T00:00:00+00:00",
        }
    )
    assert mapped["country"] == "EU"
    assert mapped["remote"] is True
    assert "Python" in mapped["description"]

    payload = {
        "jobs": [
            {
                "id": 11,
                "jobTitle": "Junior Software Developer",
                "companyName": "Acme",
                "jobGeo": "Europe",
                "url": "https://example.com/jobs/11",
                "jobDescription": "Python backend developer role with SQL",
                "jobIndustry": ["Engineering"],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    source = JobicySource(max_jobs=10, transport=transport)
    jobs = source.fetch_jobs(["Software Developer"])
    assert len(jobs) == 1
    assert jobs[0].source == "Jobicy"
    assert jobs[0].country == "EU"


def test_adzuna_jooble_careerjet_require_keys() -> None:
    assert AdzunaSource(app_id="", app_key="").implemented is False
    assert JoobleSource(api_key="").implemented is False
    assert CareerjetSource(api_key="").implemented is False

    adz = map_adzuna_raw(
        {
            "id": "99",
            "title": "Data Analyst",
            "company": {"display_name": "Firma"},
            "location": {"display_name": "Berlin, Germany"},
            "description": "SQL Power BI",
            "redirect_url": "https://example.com/a",
            "created": "2026-08-01T12:00:00Z",
        },
        market="DE",
    )
    assert adz["country"] == "DE"
    assert adz["company"] == "Firma"

    jo = map_jooble_raw(
        {
            "id": "1",
            "title": "IT Support",
            "company": "Helpdesk GmbH",
            "location": "Munich",
            "snippet": "Windows Active Directory",
            "link": "https://example.com/j",
        },
        market="DE",
    )
    assert jo["country"] == "DE"

    cj = map_careerjet_raw(
        {
            "title": "System Administrator",
            "company": "Ops AG",
            "locations": "Zurich",
            "description": "Linux networking",
            "url": "https://example.com/c",
        },
        market="CH",
    )
    assert cj["country"] == "CH"


def test_remotive_country_inference() -> None:
    de = map_remotive_raw(
        {
            "id": 1,
            "title": "Backend Engineer",
            "company_name": "X",
            "candidate_required_location": "Germany",
            "url": "https://example.com/r",
            "description": "Python",
        }
    )
    assert de["country"] == "DE"
    assert de["remote"] is True


def test_source_quota_daily_budget() -> None:
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_file = Path(tmp.name)
    original = source_quota.db_session.DATABASE_PATH
    source_quota.db_session.DATABASE_PATH = db_file
    try:
        assert source_quota.can_request("Adzuna", daily_limit=2) is True
        source_quota.record_requests("Adzuna", 1)
        source_quota.record_requests("Adzuna", 1)
        assert source_quota.get_used("Adzuna") == 2
        assert source_quota.can_request("Adzuna", daily_limit=2) is False
        assert source_quota.remaining("Adzuna", daily_limit=2) == 0
    finally:
        source_quota.db_session.DATABASE_PATH = original
        quota_file = db_file.parent / "source_quota.json"
        if quota_file.exists():
            quota_file.unlink()
        db_file.unlink(missing_ok=True)


def test_manual_portal_links_include_big_four() -> None:
    payload = build_manual_portal_links(
        markets=["DE"],
        queries=["Software Developer"],
    )
    portals = {item["portal"] for item in payload["portals"]}
    assert {"StepStone", "Indeed", "LinkedIn", "Glassdoor", "Make it in Germany"} <= portals
    assert all(item["url"].startswith("http") for item in payload["portals"])


def run_all() -> None:
    tests = [
        test_markets_and_refresh_plan_are_compact,
        test_jobicy_mapper_and_mock_fetch,
        test_adzuna_jooble_careerjet_require_keys,
        test_remotive_country_inference,
        test_source_quota_daily_budget,
        test_manual_portal_links_include_big_four,
    ]
    for test in tests:
        test()
    print(f"Cross-country source tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
