"""Tests for duplicate detection and safe merge behavior."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Job, JobSourceReference
from app.services.deduplication import (
    build_fingerprint,
    list_source_links,
    normalize_company_for_dedup,
    normalize_location_for_dedup,
    normalize_title_for_dedup,
    upsert_normalized_job,
)
from app.sources.normalized_job import NormalizedJob

# Register models on metadata.
import app.models.job  # noqa: F401
import app.models.job_source_reference  # noqa: F401


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _job(**kwargs) -> NormalizedJob:
    now = datetime.now(timezone.utc)
    defaults = {
        "source": "Arbeitnow",
        "source_job_id": "abc-1",
        "title": "Junior Software Engineer",
        "company": "Example GmbH",
        "location": "Berlin",
        "description": "We are hiring a junior engineer.",
        "job_url": "https://www.arbeitnow.com/jobs/abc-1",
        "first_seen_at": now,
        "last_seen_at": now,
        "remote": False,
        "hybrid": False,
        "match_score": 80,
        "match_category": "Gut passend",
        "status": "new",
    }
    defaults.update(kwargs)
    return NormalizedJob(**defaults)


def test_normalization_helpers() -> None:
    assert normalize_company_for_dedup("Example GmbH") == normalize_company_for_dedup(
        "EXAMPLE  GmbH"
    )
    assert normalize_title_for_dedup("Junior Software Engineer (m/w/d)") == (
        normalize_title_for_dedup("Junior Software Engineer m/w/d")
    )
    assert normalize_title_for_dedup("Junior Software Engineer (m/w/d)") == (
        normalize_title_for_dedup("Junior Software Engineer")
    )
    assert normalize_location_for_dedup("Berlin, Germany") == "berlin"
    assert normalize_location_for_dedup("Berlin, Deutschland") == "berlin"
    assert normalize_location_for_dedup("Berlin") == "berlin"
    assert build_fingerprint("Example GmbH", "Junior Software Engineer", "Berlin") == (
        build_fingerprint("EXAMPLE GmbH", "Junior Software Engineer (m/w/d)", "Berlin, Germany")
    )


def test_identical_and_whitespace_case_duplicates() -> None:
    db = _session()
    first = upsert_normalized_job(db, _job())
    second = upsert_normalized_job(
        db,
        _job(
            company="EXAMPLE  GmbH",
            title="Junior Software Engineer",
            location="Berlin",
            source="Arbeitsagentur",
            source_job_id="AA-1",
            job_url="https://www.arbeitsagentur.de/jobs/AA-1",
        ),
    )
    assert first.action == "new"
    assert second.action == "cross_source_duplicate"
    assert second.job_id == first.job_id
    assert second.source_reference_added is True
    assert len(db.scalars(select(Job)).all()) == 1


def test_mw_d_and_location_variants() -> None:
    db = _session()
    first = upsert_normalized_job(db, _job(title="Junior Software Engineer (m/w/d)"))
    second = upsert_normalized_job(
        db,
        _job(
            source="GermanTechJobs",
            source_job_id="gtj-9",
            title="Junior Software Engineer",
            location="Berlin, Germany",
            job_url="https://germantechjobs.de/jobs/9",
        ),
    )
    assert second.action == "cross_source_duplicate"
    assert second.job_id == first.job_id
    # Original display title preserved on primary record.
    assert db.get(Job, first.job_id).title == "Junior Software Engineer (m/w/d)"


def test_same_source_job_id_and_same_url() -> None:
    db = _session()
    created = upsert_normalized_job(db, _job(source_job_id="same-id"))
    by_id = upsert_normalized_job(
        db,
        _job(
            source_job_id="same-id",
            description="Updated longer description for the same listing.",
            remote=True,
        ),
    )
    assert by_id.action == "exact_duplicate"
    assert by_id.job_id == created.job_id
    assert db.get(Job, created.job_id).remote is True

    by_url = upsert_normalized_job(
        db,
        _job(
            source="OtherSource",
            source_job_id="other-99",
            job_url="https://www.arbeitnow.com/jobs/abc-1",
            title="Completely Different Title",
            company="Other Co",
            location="Hamburg",
        ),
    )
    assert by_url.action == "cross_source_duplicate"
    assert by_url.job_id == created.job_id


def test_senior_and_team_lead_not_merged() -> None:
    db = _session()
    junior = upsert_normalized_job(db, _job(title="Software Engineer", source_job_id="j1"))
    senior = upsert_normalized_job(
        db,
        _job(
            title="Senior Software Engineer",
            source_job_id="s1",
            job_url="https://www.arbeitnow.com/jobs/s1",
        ),
    )
    lead = upsert_normalized_job(
        db,
        _job(
            title="IT Support Team Lead",
            company="Example GmbH",
            location="Berlin",
            source_job_id="l1",
            job_url="https://www.arbeitnow.com/jobs/l1",
        ),
    )
    support = upsert_normalized_job(
        db,
        _job(
            title="IT Support",
            company="Example GmbH",
            location="Berlin",
            source_job_id="t1",
            job_url="https://www.arbeitnow.com/jobs/t1",
        ),
    )
    assert junior.action == "new"
    assert senior.action == "new"
    assert lead.action == "new"
    assert support.action == "new"
    assert len({junior.job_id, senior.job_id, lead.job_id, support.job_id}) == 4


def test_different_companies_not_merged() -> None:
    db = _session()
    a = upsert_normalized_job(db, _job(company="Alpha GmbH", source_job_id="a1"))
    b = upsert_normalized_job(
        db,
        _job(
            company="Beta GmbH",
            source_job_id="b1",
            job_url="https://www.arbeitnow.com/jobs/b1",
        ),
    )
    assert a.job_id != b.job_id
    assert b.action == "new"


def test_status_preserved_and_last_seen_updated() -> None:
    db = _session()
    created = upsert_normalized_job(db, _job())
    job = db.get(Job, created.job_id)
    old_seen = datetime.now(timezone.utc) - timedelta(days=3)
    job.status = "applied"
    job.last_seen_at = old_seen
    db.commit()

    result = upsert_normalized_job(
        db,
        _job(
            source="Arbeitsagentur",
            source_job_id="AA-22",
            job_url="https://www.arbeitsagentur.de/jobs/AA-22",
            description="",  # must not wipe existing description
        ),
    )
    updated = db.get(Job, created.job_id)
    assert result.action == "cross_source_duplicate"
    assert updated.status == "applied"
    updated_seen = updated.last_seen_at
    if updated_seen.tzinfo is None:
        updated_seen = updated_seen.replace(tzinfo=timezone.utc)
    assert updated_seen > old_seen
    assert updated.description == "We are hiring a junior engineer."

    job.status = "interview"
    db.commit()
    again = upsert_normalized_job(
        db,
        _job(
            source="GermanTechJobs",
            source_job_id="gtj-22",
            job_url="https://germantechjobs.de/jobs/22",
        ),
    )
    assert db.get(Job, created.job_id).status == "interview"
    assert again.source_reference_added is True


def test_source_references_preserved_and_new_job_created() -> None:
    db = _session()
    first = upsert_normalized_job(db, _job())
    second = upsert_normalized_job(
        db,
        _job(
            source="Arbeitsagentur",
            source_job_id="AA-77",
            job_url="https://www.arbeitsagentur.de/jobs/AA-77",
            hybrid=True,
            match_score=90,
            match_category="Sehr passend",
        ),
    )
    job = db.get(Job, first.job_id)
    refs = db.scalars(
        select(JobSourceReference).where(JobSourceReference.job_id == job.id)
    ).all()
    assert second.source_reference_added is True
    assert len(refs) == 1
    assert refs[0].source == "Arbeitsagentur"
    assert job.hybrid is True
    assert job.match_score == 90

    links = list_source_links(db, job)
    assert len(links) == 2
    assert {link["source"] for link in links} == {"Arbeitnow", "Arbeitsagentur"}

    brand_new = upsert_normalized_job(
        db,
        _job(
            company="Other Corp",
            title="Junior QA Engineer",
            location="München",
            source_job_id="qa-1",
            job_url="https://www.arbeitnow.com/jobs/qa-1",
        ),
    )
    assert brand_new.action == "new"
    assert brand_new.job_id != first.job_id
    assert len(db.scalars(select(Job)).all()) == 2


def run_all() -> None:
    tests = [
        test_normalization_helpers,
        test_identical_and_whitespace_case_duplicates,
        test_mw_d_and_location_variants,
        test_same_source_job_id_and_same_url,
        test_senior_and_team_lead_not_merged,
        test_different_companies_not_merged,
        test_status_preserved_and_last_seen_updated,
        test_source_references_preserved_and_new_job_created,
    ]
    for test in tests:
        test()
    print(f"Deduplication tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
