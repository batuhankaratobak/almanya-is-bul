"""
Live Arbeitnow integration test.

Skipped unless RUN_LIVE_SOURCE_TESTS=1.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_mvp_refresh_queries
from app.sources.arbeitnow import ArbeitnowSource


def test_live_arbeitnow_limited_fetch() -> None:
    if os.getenv("RUN_LIVE_SOURCE_TESTS") != "1":
        print("SKIP live Arbeitnow test (set RUN_LIVE_SOURCE_TESTS=1)")
        return

    source = ArbeitnowSource(max_pages=1, max_jobs=30)
    jobs = source.fetch_jobs(get_mvp_refresh_queries())
    assert jobs, "Expected at least one Germany-relevant IT job from Arbeitnow"
    assert all(job.source == "Arbeitnow" for job in jobs)
    assert all(job.job_url.startswith("https://") for job in jobs)
    print(
        "LIVE_OK",
        {
            "fetched": len(jobs),
            "sample_title": jobs[0].title,
            "sample_company": jobs[0].company,
            "sample_location": jobs[0].location,
            "sample_url": jobs[0].job_url,
            "sample_score": jobs[0].match_score,
        },
    )


if __name__ == "__main__":
    test_live_arbeitnow_limited_fetch()
