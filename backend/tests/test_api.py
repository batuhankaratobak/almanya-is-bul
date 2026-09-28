"""API tests using an isolated temporary SQLite database."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.db import session as db_session
from app.main import app
from app.models import Job
from app.services.scoring import detect_role_category


def _make_client():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_session.configure_database(db_path)
    db_session.init_db()
    return TestClient(app), db_path


def _seed_jobs() -> None:
    db = db_session.SessionLocal()
    now = datetime.now(timezone.utc)
    samples = [
        Job(
            source="Arbeitnow",
            source_job_id="j1",
            title="Junior Software Developer",
            company="Alpha GmbH",
            location="Berlin",
            description="We need a junior engineer. Requirements and skills.",
            job_url="https://example.com/j1",
            date_posted=now,
            first_seen_at=now,
            last_seen_at=now,
            remote=True,
            hybrid=False,
            job_language="en",
            german_requirement="B2|preferred",
            english_requirement="null|required",
            experience_level="junior",
            match_score=90,
            match_category="Sehr passend",
            fingerprint="fp1",
            status="new",
        ),
        Job(
            source="Arbeitsagentur",
            source_job_id="j2",
            title="IT Support Mitarbeiter",
            company="Beta AG",
            location="München",
            description="Wir suchen IT Support. Aufgaben und Anforderungen.",
            job_url="https://example.com/j2",
            date_posted=now,
            first_seen_at=now,
            last_seen_at=now,
            remote=False,
            hybrid=True,
            job_language="de",
            german_requirement="B1|required",
            experience_level="junior",
            match_score=75,
            match_category="Gut passend",
            fingerprint="fp2",
            status="applied",
        ),
        Job(
            source="GermanTechJobs",
            source_job_id="j3",
            title="Senior Software Engineer",
            company="Gamma GmbH",
            location="Hamburg",
            description="Senior role with 5+ years.",
            job_url="https://example.com/j3",
            date_posted=now,
            first_seen_at=now,
            last_seen_at=now,
            remote=False,
            hybrid=False,
            job_language="en",
            german_requirement="C1|required",
            experience_level="senior",
            match_score=30,
            match_category="Weniger passend",
            fingerprint="fp3",
            status="reviewing",
        ),
    ]
    db.add_all(samples)
    db.commit()
    db.close()


def test_health_returns_success() -> None:
    client, _ = _make_client()
    with client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


def test_jobs_pagination_and_filters() -> None:
    client, _ = _make_client()
    _seed_jobs()
    with client:
        response = client.get("/jobs", params={"limit": 2, "offset": 0, "sort": "score"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 3
        assert payload["limit"] == 2
        assert payload["offset"] == 0
        assert len(payload["items"]) == 2
        assert payload["items"][0]["match_score"] >= payload["items"][1]["match_score"]

        search = client.get("/jobs", params={"search": "Alpha"})
        assert search.status_code == 200
        assert search.json()["total"] == 1
        assert search.json()["items"][0]["company"] == "Alpha GmbH"

        category = client.get("/jobs", params={"category": "it_support"})
        assert category.status_code == 200
        assert category.json()["total"] == 1
        assert detect_role_category(category.json()["items"][0]["title"]) == "it_support"

        status_filter = client.get("/jobs", params={"status": "applied"})
        assert status_filter.status_code == 200
        assert status_filter.json()["total"] == 1
        assert status_filter.json()["items"][0]["status"] == "applied"

        scored = client.get("/jobs", params={"min_score": 80})
        assert scored.status_code == 200
        assert scored.json()["total"] == 1
        assert scored.json()["items"][0]["match_score"] >= 80

        band = client.get("/jobs", params={"min_score": 70, "max_score": 84})
        assert band.status_code == 200
        assert band.json()["total"] == 1
        assert 70 <= band.json()["items"][0]["match_score"] <= 84

        limited = client.get("/jobs", params={"limit": 500})
        assert limited.status_code == 422


def test_job_detail_and_missing() -> None:
    client, _ = _make_client()
    _seed_jobs()
    with client:
        listing = client.get("/jobs").json()["items"]
        job_id = listing[0]["id"]
        detail = client.get(f"/jobs/{job_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["id"] == job_id
        assert "positive_reasons" in body
        assert "primary_source" in body

        missing = client.get("/jobs/999999")
        assert missing.status_code == 404
        assert "not found" in missing.json()["detail"].lower()


def test_status_update_validation() -> None:
    client, _ = _make_client()
    _seed_jobs()
    with client:
        job_id = client.get("/jobs").json()["items"][0]["id"]
        ok = client.patch(f"/jobs/{job_id}/status", json={"status": "applied"})
        assert ok.status_code == 200
        assert ok.json()["status"] == "applied"

        bad = client.patch(f"/jobs/{job_id}/status", json={"status": "nope"})
        assert bad.status_code == 422

        missing = client.patch("/jobs/999999/status", json={"status": "ignored"})
        assert missing.status_code == 404


def test_stats_sources_and_refresh() -> None:
    from unittest.mock import patch

    from app.sources import SourceManager
    from app.sources.base import JobSource
    from app.sources.germantechjobs import GermanTechJobsSource
    from app.sources.jobvector import JobvectorSource
    from app.sources.make_it_in_germany import MakeItInGermanySource
    from app.sources.normalized_job import NormalizedJob

    class FakeArbeitsagentur(JobSource):
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
                    source_job_id="api-test-1",
                    title="Junior Softwareentwickler",
                    company="API Test GmbH",
                    location="Berlin",
                    description="Wir suchen Verstärkung. Aufgaben und Anforderungen.",
                    job_url="https://www.arbeitsagentur.de/jobsuche/jobdetail/api-test-1",
                    match_score=80,
                    match_category="Gut passend",
                )
            ]

    class FakeArbeitnow(JobSource):
        @property
        def name(self) -> str:
            return "Arbeitnow"

        @property
        def implemented(self) -> bool:
            return True

        def fetch_jobs(self, search_terms):
            return [
                NormalizedJob(
                    source="Arbeitnow",
                    source_job_id="an-test-1",
                    title="Junior Software Engineer",
                    company="API Test GmbH",
                    location="Berlin",
                    description="We need a junior engineer. Requirements and skills.",
                    job_url="https://www.arbeitnow.com/jobs/an-test-1",
                    match_score=78,
                    match_category="Gut passend",
                )
            ]

    class FakeAbsolventa(JobSource):
        @property
        def name(self) -> str:
            return "Absolventa"

        @property
        def implemented(self) -> bool:
            return True

        def fetch_jobs(self, search_terms):
            return []

    class FakeEures(JobSource):
        @property
        def name(self) -> str:
            return "EURES"

        @property
        def implemented(self) -> bool:
            return True

        def fetch_jobs(self, search_terms):
            return []

    def fake_manager() -> SourceManager:
        manager = SourceManager()
        manager.register(FakeArbeitsagentur())
        manager.register(FakeArbeitnow())
        manager.register(FakeAbsolventa())
        manager.register(JobvectorSource())
        manager.register(MakeItInGermanySource())
        manager.register(GermanTechJobsSource())
        manager.register(FakeEures())
        return manager

    client, _ = _make_client()
    _seed_jobs()
    with client:
        stats = client.get("/stats")
        assert stats.status_code == 200
        body = stats.json()
        assert body["total_jobs"] == 3
        assert body["excellent_matches"] == 1
        assert body["good_matches"] == 1
        assert body["poor_matches"] == 1
        assert body["applied"] == 1
        assert body["new"] == 1
        assert body["reviewing"] == 1

        sources = client.get("/sources")
        assert sources.status_code == 200
        by_name = {item["name"]: item for item in sources.json()["sources"]}
        assert set(by_name) == {
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
        }
        assert by_name["Arbeitsagentur"]["implemented"] is True
        assert by_name["Arbeitnow"]["implemented"] is True
        assert by_name["Absolventa"]["implemented"] is True
        assert by_name["EURES"]["implemented"] is True
        assert by_name["Jobicy"]["implemented"] is True
        assert by_name["Remotive"]["implemented"] is True
        assert by_name["Jooble"]["implemented"] is False
        assert by_name["Jobvector"]["implemented"] is False
        assert by_name["Make it in Germany"]["implemented"] is False
        assert by_name["GermanTechJobs"]["implemented"] is False
        assert by_name["Glassdoor"]["implemented"] is False
        assert by_name["GermanTechJobs"]["status"] == "not_implemented"

        with patch("app.services.refresh.create_default_source_manager", fake_manager):
            refresh = client.post("/jobs/refresh")
        assert refresh.status_code == 200
        payload = refresh.json()
        assert payload["status"] == "completed"
        assert payload["jobs_scanned"] >= 1
        assert "duration_seconds" in payload
        assert payload["sources"]["Arbeitsagentur"]["status"] == "success"
        assert "duration_seconds" in payload["sources"]["Arbeitsagentur"]
        assert payload["sources"]["Arbeitnow"]["status"] == "success"
        assert payload["sources"]["Absolventa"]["status"] == "success"
        assert payload["sources"]["EURES"]["status"] == "success"
        assert payload["sources"]["Jobvector"]["status"] == "not_implemented"
        assert payload["sources"]["Make it in Germany"]["status"] == "not_implemented"
        assert payload["sources"]["GermanTechJobs"]["status"] == "not_implemented"

        sources_after = client.get("/sources")
        after = {item["name"]: item for item in sources_after.json()["sources"]}
        assert after["Arbeitsagentur"]["status"] == "active"
        assert after["Arbeitnow"]["status"] == "active"
        assert after["GermanTechJobs"]["status"] == "not_implemented"


def run_all() -> None:
    tests = [
        test_health_returns_success,
        test_jobs_pagination_and_filters,
        test_job_detail_and_missing,
        test_status_update_validation,
        test_stats_sources_and_refresh,
    ]
    for test in tests:
        test()
    print(f"API tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
