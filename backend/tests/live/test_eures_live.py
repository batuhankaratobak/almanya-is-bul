"""
Live EURES integration test.

Skipped unless RUN_LIVE_SOURCE_TESTS=1.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Job
import app.models.job_source_reference  # noqa: F401
from app.services.refresh import refresh_jobs
from app.sources import SourceManager
from app.sources.eures import EuresSource


def test_live_eures_limited_fetch() -> None:
    if os.getenv("RUN_LIVE_SOURCE_TESTS") != "1":
        print("SKIP live EURES test (set RUN_LIVE_SOURCE_TESTS=1)")
        return

    source = EuresSource(max_results_per_query=5, max_total_jobs=8, search_concurrency=2)
    jobs = source.fetch_jobs(["Junior Software Developer", "Softwareentwickler"])
    assert jobs, "Expected at least one live EURES job"
    assert all(job.source == "EURES" for job in jobs)
    assert all("eures" in job.job_url for job in jobs)

    import httpx

    probe = httpx.get(jobs[0].job_url, follow_redirects=True, timeout=30)
    assert probe.status_code < 400, f"Job URL not reachable: {jobs[0].job_url}"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    manager = SourceManager()
    manager.register(source)
    result = refresh_jobs(
        db,
        manager=manager,
        search_terms=["Junior Software Developer"],
    )
    stored = list(db.scalars(select(Job)).all())
    print(
        "LIVE_OK",
        {
            "fetched": len(jobs),
            "stored": len(stored),
            "sample_title": jobs[0].title,
            "sample_company": jobs[0].company,
            "sample_location": jobs[0].location,
            "sample_url": jobs[0].job_url,
            "duration": result.sources["EURES"].duration_seconds,
        },
    )
    assert result.sources["EURES"].status == "success"
    assert stored


if __name__ == "__main__":
    test_live_eures_limited_fetch()
