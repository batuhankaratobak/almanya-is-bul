"""Tests for local candidate profile + rescore."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.db import session as db_session
from app.main import app
from app.models import Job
from app.services.candidate_profile import get_default_profile, load_profile, save_profile
from app.services.rescore import rescore_all_jobs


def _make_client():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_session.configure_database(db_path)
    db_session.init_db()
    return TestClient(app), db_path


def test_default_profile_roundtrip() -> None:
    client, db_path = _make_client()
    with client:
        response = client.get("/profile")
        assert response.status_code == 200
        body = response.json()
        assert "Python" in body["skills"]
        assert "software_development" in body["target_categories"]
        assert (db_path.parent / "candidate_profile.json").exists()


def test_save_profile_rescored_jobs() -> None:
    client, _ = _make_client()
    with client:
        db = db_session.SessionLocal()
        db.add(
            Job(
                source="test",
                source_job_id="p1",
                title="Junior Software Developer",
                company="Profil GmbH",
                location="Berlin",
                description="Python SQL React Git required.",
                job_url="https://example.com/p1",
                match_score=40,
                match_category="Düşük Uygunluk",
                status="applied",
            )
        )
        db.commit()
        status_before = db.query(Job).one().status
        db.close()

        profile = get_default_profile()
        profile["skills"] = ["Python", "SQL", "React", "Git"]
        saved = client.put("/profile", json=profile)
        assert saved.status_code == 200
        payload = saved.json()
        assert payload["rescore"]["jobs_total"] == 1
        assert payload["rescore"]["jobs_updated"] >= 1

        jobs = client.get("/jobs").json()["items"]
        assert len(jobs) == 1
        assert jobs[0]["match_score"] > 40
        assert jobs[0]["status"] == status_before == "applied"


def test_rescore_preserves_status() -> None:
    client, _ = _make_client()
    with client:
        db = db_session.SessionLocal()
        db.add(
            Job(
                source="test",
                source_job_id="p2",
                title="Senior Lead Principal Engineer",
                company="X",
                location="München",
                description="Kubernetes AWS 8 years",
                job_url="https://example.com/p2",
                match_score=90,
                match_category="Çok Uygun",
                status="interview",
            )
        )
        db.commit()
        db.close()

        profile = load_profile()
        result = rescore_all_jobs(db_session.SessionLocal(), profile=profile)
        assert result["jobs_total"] == 1
        db = db_session.SessionLocal()
        job = db.query(Job).one()
        assert job.status == "interview"
        assert job.match_score < 70
        db.close()


def run_all() -> None:
    tests = [
        test_default_profile_roundtrip,
        test_save_profile_rescored_jobs,
        test_rescore_preserves_status,
    ]
    for test in tests:
        test()
    print(f"Profile tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
