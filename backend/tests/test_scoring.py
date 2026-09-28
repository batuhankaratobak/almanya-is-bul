"""Tests for profile-based job relevance scoring."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.candidate_profile import get_default_profile
from app.services.scoring import apply_score, detect_role_category, score_category, score_job
from app.sources.normalized_job import NormalizedJob


def _job(**kwargs) -> NormalizedJob:
    defaults = {
        "source": "test",
        "title": "Role",
        "company": "Firma",
        "location": "Berlin",
        "description": "",
        "job_url": "https://example.com/job",
        "source_job_id": "1",
    }
    defaults.update(kwargs)
    return NormalizedJob(**defaults)


def _profile(**overrides):
    data = get_default_profile()
    data.update(overrides)
    return data


def test_score_bands() -> None:
    assert score_category(95) == "Mükemmel Eşleşme"
    assert score_category(85) == "Çok Uygun"
    assert score_category(75) == "Uygun"
    assert score_category(60) == "Olası"
    assert score_category(40) == "Düşük Uygunluk"


def test_junior_software_with_skills_scores_well_not_perfect() -> None:
    job = _job(
        title="Junior Softwareentwickler",
        description=(
            "Python and SQL required. React experience helpful. "
            "Deutsch B1. Hybrid work. Informatik degree. 0-2 Jahre Berufserfahrung."
        ),
        german_requirement="B1|required",
        experience_level="junior",
        hybrid=True,
        job_language="de",
        location="Berlin",
    )
    result = score_job(job, profile=_profile())
    assert 70 <= result.score <= 94
    assert result.category in {"Uygun", "Çok Uygun", "Mükemmel Eşleşme"}
    assert "Python" in result.matched_skills
    assert "Hedef pozisyon alanıyla eşleşiyor" in result.positive_reasons
    # Perfect 100 should be extremely rare
    assert result.score < 100


def test_missing_info_is_neutral() -> None:
    job = _job(
        title="Softwareentwickler",
        description="Allgemeine Aufgaben.",
        german_requirement="null|unknown",
        english_requirement="null|unknown",
    )
    result = score_job(job, profile=_profile())
    # No automatic German-ad penalty; no invented years bonus.
    assert "Almanca C1 gerekiyor" not in result.negative_reasons
    assert result.score < 85


def test_senior_strongly_penalized() -> None:
    job = _job(
        title="Senior Software Engineer",
        description="Python SQL React. 5+ years required.",
        experience_level="senior",
    )
    result = score_job(job, profile=_profile(preferred_max_experience_years=2))
    assert result.score < 55
    assert any("Senior" in reason or "5" in reason for reason in result.negative_reasons)


def test_experience_mismatch_penalties() -> None:
    profile = _profile(preferred_max_experience_years=2)
    mild = score_job(
        _job(title="Softwareentwickler", description="mindestens 3 Jahre Berufserfahrung Python"),
        profile=profile,
    )
    hard = score_job(
        _job(title="Softwareentwickler", description="mindestens 5 Jahre Berufserfahrung Python"),
        profile=profile,
    )
    assert mild.score > hard.score


def test_role_categories_classified_correctly() -> None:
    assert detect_role_category("IT Support Mitarbeiter") == "it_support"
    assert detect_role_category("Junior SOC Analyst") == "cybersecurity"
    assert detect_role_category("Junior QA Engineer") == "qa_testing"
    assert detect_role_category("Systemadministrator") == "system_administration"
    assert (
        detect_role_category(
            "Junior Software Developer",
            "You will learn about application security best practices.",
        )
        == "software_development"
    )


def test_skill_overlap_and_missing() -> None:
    job = _job(
        title="Junior Backend Developer",
        description="Python, FastAPI, Kubernetes and AWS required.",
    )
    result = score_job(job, profile=_profile(skills=["Python", "FastAPI", "SQL"]))
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.matched_skills
    assert "Kubernetes" in result.missing_skills
    assert "AWS" in result.missing_skills


def test_apply_score_writes_fields() -> None:
    job = _job(title="Junior Software Developer", description="Python SQL Git")
    result = apply_score(job, profile=_profile())
    assert job.match_score == result.score
    assert job.match_category == result.category
    assert "matched_skills" in (job.raw or {}).get("match_reasons", {})


def test_german_level_compared_to_profile() -> None:
    job = _job(
        title="Junior Softwareentwickler",
        description="Python SQL. Deutsch C1 erforderlich.",
        german_requirement="C1|required",
    )
    low = score_job(job, profile=_profile(german_level="B1"))
    high = score_job(job, profile=_profile(german_level="C1"))
    assert high.score > low.score
    assert any("Almanca C1" in reason for reason in low.negative_reasons)


def run_all() -> None:
    tests = [
        test_score_bands,
        test_junior_software_with_skills_scores_well_not_perfect,
        test_missing_info_is_neutral,
        test_senior_strongly_penalized,
        test_experience_mismatch_penalties,
        test_role_categories_classified_correctly,
        test_skill_overlap_and_missing,
        test_apply_score_writes_fields,
        test_german_level_compared_to_profile,
    ]
    for test in tests:
        test()
    print(f"Scoring tests passed ({len(tests)} tests).")


if __name__ == "__main__":
    run_all()
