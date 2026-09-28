"""Simple database initialization and Job model smoke test."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import inspect, select

from app.db import DATABASE_PATH, SessionLocal, check_db_connection, init_db
from app.models import ApplicationStatus, Job, JobSourceReference


REQUIRED_COLUMNS = {
    "id",
    "source",
    "source_job_id",
    "title",
    "company",
    "location",
    "description",
    "job_url",
    "date_posted",
    "first_seen_at",
    "last_seen_at",
    "remote",
    "hybrid",
    "employment_type",
    "job_language",
    "german_requirement",
    "english_requirement",
    "experience_level",
    "match_score",
    "match_category",
    "fingerprint",
    "status",
    "created_at",
    "updated_at",
}


def test_database() -> None:
    db_path = init_db()
    assert db_path == DATABASE_PATH
    assert DATABASE_PATH.exists(), f"SQLite file missing: {DATABASE_PATH}"

    health = check_db_connection()
    assert health["ok"] is True
    assert health["exists"] is True

    inspector = inspect(SessionLocal().get_bind())
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    missing = REQUIRED_COLUMNS - columns
    assert not missing, f"Missing columns: {sorted(missing)}"

    indexes = {index["name"] for index in inspector.get_indexes("jobs")}
    expected_indexes = {
        "ix_jobs_job_url",
        "ix_jobs_company_title_location",
        "ix_jobs_fingerprint",
        "ix_jobs_source_job_id",
        "ix_jobs_status",
        "ix_jobs_match_score",
        "ix_jobs_job_language",
        "ix_jobs_location",
        "ix_jobs_source",
        "ix_jobs_german_requirement",
        "ix_jobs_remote",
    }
    missing_indexes = expected_indexes - indexes
    assert not missing_indexes, f"Missing indexes: {sorted(missing_indexes)}"

    tables = set(inspector.get_table_names())
    assert "job_source_references" in tables
    ref_columns = {
        column["name"] for column in inspector.get_columns("job_source_references")
    }
    assert {
        "id",
        "job_id",
        "source",
        "source_job_id",
        "job_url",
        "first_seen_at",
        "last_seen_at",
    }.issubset(ref_columns)

    db = SessionLocal()
    try:
        job = Job(
            source="test",
            source_job_id="phase2-smoke",
            title="Junior Softwareentwickler",
            company="Test GmbH",
            location="Berlin",
            description="Originalbeschreibung bleibt unverändert.",
            job_url="https://example.com/jobs/phase2-smoke",
            remote=False,
            hybrid=True,
            status=ApplicationStatus.NEW.value,
            match_score=0,
            fingerprint="phase2-fingerprint",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.id is not None
        assert job.first_seen_at is not None
        assert job.last_seen_at is not None
        assert job.status == ApplicationStatus.NEW.value
        assert job.fingerprint == "phase2-fingerprint"

        ref = JobSourceReference(
            job_id=job.id,
            source="Arbeitnow",
            source_job_id="phase2-ref",
            job_url="https://example.com/jobs/phase2-ref",
        )
        db.add(ref)
        db.commit()

        loaded = db.scalar(select(Job).where(Job.source_job_id == "phase2-smoke"))
        assert loaded is not None
        assert loaded.title == "Junior Softwareentwickler"
        assert loaded.company == "Test GmbH"

        db.delete(ref)
        db.delete(loaded)
        db.commit()
    finally:
        db.close()

    print("Database test passed.")
    print(f"SQLite file: {DATABASE_PATH}")


if __name__ == "__main__":
    test_database()
