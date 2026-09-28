"""
Live Arbeitsagentur integration test.

Skipped unless RUN_LIVE_SOURCE_TESTS=1.
Does not run as part of the normal unit suite.
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
from app.sources.arbeitsagentur import ArbeitsagenturSource
from app.sources.arbeitsagentur_client import ArbeitsagenturClient


def test_live_arbeitsagentur_limited_fetch() -> None:
    if os.getenv("RUN_LIVE_SOURCE_TESTS") != "1":
        print("SKIP live Arbeitsagentur test (set RUN_LIVE_SOURCE_TESTS=1)")
        return

    client = ArbeitsagenturClient(timeout=30)
    source = ArbeitsagenturSource(
        client=client,
        max_results_per_query=5,
        max_total_jobs=8,
        fetch_details=True,
    )
    jobs = source.fetch_jobs(["Junior Softwareentwickler"])
    assert jobs, "Expected at least one live Arbeitsagentur job"
    assert all(job.source == "Arbeitsagentur" for job in jobs)
    assert all(job.job_url.startswith("https://") for job in jobs)

    # Verify at least one job URL responds.
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
        search_terms=["Junior Softwareentwickler"],
    )
    stored = list(db.scalars(select(Job)).all())
    print(
        "LIVE_OK",
        {
            "fetched": len(jobs),
            "jobs_scanned": result.jobs_scanned,
            "new_jobs": result.new_jobs,
            "stored": len(stored),
            "sample_title": jobs[0].title,
            "sample_url": jobs[0].job_url,
            "source_status": result.sources["Arbeitsagentur"].status,
        },
    )
    assert result.sources["Arbeitsagentur"].status == "success"
    assert result.new_jobs >= 1
    assert stored


if __name__ == "__main__":
    test_live_arbeitsagentur_limited_fetch()
