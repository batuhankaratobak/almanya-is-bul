"""Tests for the job normalization layer (synthetic fixtures only)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.normalization import (
    detect_employment_type,
    detect_english_requirement,
    detect_experience_level,
    detect_german_requirement,
    detect_job_language,
    detect_work_model,
    normalize_arbeitsagentur_job,
    normalize_arbeitnow_job,
    normalize_germantechjobs_job,
    normalize_location,
    normalize_raw_job,
    normalize_text,
    normalize_url,
    parse_date,
)


def test_normalize_text_and_missing_fields() -> None:
    assert normalize_text("  Junior   Softwareentwickler  ") == "Junior Softwareentwickler"
    assert normalize_text(None) == ""
    assert normalize_text("") == ""

    job = normalize_raw_job({}, source="test")
    assert job.title == ""
    assert job.company == ""
    assert job.location == ""
    assert job.job_url == ""
    assert job.date_posted is None
    assert job.description == ""
    assert job.status == "new"
    assert 0 <= job.match_score <= 100
    assert job.match_category is not None


def test_german_job_normalization() -> None:
    raw = {
        "titel": "Junior Softwareentwickler",
        "arbeitgeber": "Beispiel GmbH",
        "arbeitsort": "Berlin, Deutschland",
        "stellenbeschreibung": (
            "Wir suchen Verstärkung. Aufgaben und Anforderungen: "
            "Kenntnisse in Python. Berufserfahrung von Vorteil. "
            "Bewerbung an das Unternehmen. Deutsch B2 erforderlich. "
            "Homeoffice möglich. Vollzeit."
        ),
        "externeUrl": "https://www.arbeitsagentur.de/jobs/123",
        "referenznummer": "AA-123",
        "aktuelleVeroeffentlichungsdatum": "08.08.2026",
        "arbeitszeit": "Vollzeit",
    }
    job = normalize_arbeitsagentur_job(raw)

    assert job.source == "Arbeitsagentur"
    assert job.source_job_id == "AA-123"
    assert job.title == "Junior Softwareentwickler"
    assert job.company == "Beispiel GmbH"
    assert job.location == "Berlin, Deutschland"
    assert job.location_normalized == "berlin"
    assert "Wir suchen Verstärkung" in job.description  # original text preserved
    assert job.job_language == "de"
    assert job.experience_level in {"junior", "entry_level"}
    assert job.german_requirement == "B2|required"
    assert job.employment_type == "full_time"
    assert job.remote is True
    assert job.date_posted == datetime(2026, 8, 8, tzinfo=timezone.utc)


def test_english_job_normalization() -> None:
    raw = {
        "title": "Junior Backend Developer",
        "company_name": "Example AG",
        "location": "Munich, Germany",
        "description": (
            "We are looking for a teammate. Responsibilities and requirements: "
            "skills in Python. Experience with APIs. Apply via the company portal. "
            "English required. Fluent English. Fully remote. Full-time."
        ),
        "url": "https://www.arbeitnow.com/jobs/junior-backend",
        "slug": "junior-backend",
        "created_at": "2026-08-08T10:30:00",
        "remote": True,
        "job_types": ["full_time"],
    }
    job = normalize_arbeitnow_job(raw)

    assert job.source == "Arbeitnow"
    assert job.title == "Junior Backend Developer"
    assert job.job_language == "en"
    assert job.english_requirement == "null|required"
    assert job.remote is True
    assert job.experience_level == "junior"
    assert job.employment_type == "full_time"
    assert job.date_posted == datetime(2026, 8, 8, 10, 30, tzinfo=timezone.utc)


def test_mixed_language_job_detection() -> None:
    language = detect_job_language(
        "Junior Software Engineer",
        (
            "We are looking for support. Requirements and responsibilities included. "
            "Wir bieten Aufgaben und Anforderungen mit Berufserfahrung. "
            "Bewerbung über das Unternehmen."
        ),
    )
    assert language == "de/en"

    job = normalize_germantechjobs_job(
        {
            "id": 99,
            "title": "Junior Security Engineer",
            "company": {"name": "SecureTech"},
            "city": "Hamburg",
            "description": (
                "Requirements and experience needed. Skills matter. "
                "Aufgaben und Anforderungen: Kenntnisse in IT Sicherheit. "
                "Bewerbung willkommen."
            ),
            "url": "https://germantechjobs.de/jobs/99",
            "postedAt": "2026-08-08",
            "workModel": "Hybrid",
            "employmentType": "Vollzeit",
        }
    )
    assert job.source == "GermanTechJobs"
    assert job.job_language == "de/en"
    assert job.hybrid is True
    assert job.employment_type == "full_time"


def test_location_normalization() -> None:
    samples = [
        "Berlin, Germany",
        "Berlin, Deutschland",
        "Berlin",
        "Berlin DE",
    ]
    keys = {normalize_location(sample)[1] for sample in samples}
    assert keys == {"berlin"}
    assert normalize_location("Berlin, Germany")[0] == "Berlin, Germany"


def test_url_normalization() -> None:
    assert normalize_url("  https://example.com/jobs/1?ref=x  ") == (
        "https://example.com/jobs/1?ref=x"
    )
    assert normalize_url("") == ""
    assert normalize_url(None) == ""
    assert normalize_url("not-a-url") == ""


def test_date_normalization() -> None:
    assert parse_date("2026-08-08") == datetime(2026, 8, 8, tzinfo=timezone.utc)
    assert parse_date("2026-08-08T10:30:00") == datetime(
        2026, 8, 8, 10, 30, tzinfo=timezone.utc
    )
    assert parse_date("08.08.2026") == datetime(2026, 8, 8, tzinfo=timezone.utc)
    assert parse_date("08/08/2026") == datetime(2026, 8, 8, tzinfo=timezone.utc)
    assert parse_date(None) is None
    assert parse_date("") is None


def test_german_b2_and_c1_detection() -> None:
    b2 = detect_german_requirement("Deutschkenntnisse B2 erforderlich für die Rolle.")
    assert b2.level == "B2"
    assert b2.status == "required"
    assert b2.to_storage() == "B2|required"

    c1 = detect_german_requirement("Sehr gute Deutschkenntnisse C1 sind notwendig.")
    assert c1.level == "C1"
    assert c1.status == "required"

    preferred = detect_german_requirement("Deutsch von Vorteil")
    assert preferred.status == "preferred"


def test_english_requirement_detection() -> None:
    required = detect_english_requirement("Fluent English required for customer calls.")
    assert required.status == "required"

    preferred = detect_english_requirement("Good command of English preferred.")
    assert preferred.status == "preferred"

    leveled = detect_english_requirement("English B2")
    assert leveled.level == "B2"
    assert leveled.status == "required"


def test_junior_and_senior_detection() -> None:
    assert detect_experience_level("Junior Softwareentwickler Berufseinsteiger") in {
        "junior",
        "entry_level",
    }
    assert detect_experience_level("Graduate Software Engineer Entry Level") == "entry_level"
    assert detect_experience_level("Senior Software Engineer 5+ years") == "senior"
    assert detect_experience_level("Engineering Lead / Principal Engineer") == "lead"
    assert detect_experience_level("Software Developer") == "unknown"


def test_remote_and_hybrid_detection() -> None:
    remote, hybrid = detect_work_model("Fully remote position in Germany.")
    assert remote is True
    assert hybrid is False

    remote, hybrid = detect_work_model("Hybrides Arbeiten / teilweise Homeoffice in Berlin.")
    assert hybrid is True

    remote, hybrid = detect_work_model("We use remote debugging tools in the office.")
    assert remote is False


def test_employment_type_normalization() -> None:
    assert detect_employment_type("Vollzeit") == "full_time"
    assert detect_employment_type("Teilzeit") == "part_time"
    assert detect_employment_type("Werkstudent") == "working_student"
    assert detect_employment_type("Praktikum") == "internship"
    assert detect_employment_type("Ausbildung") == "apprenticeship"
    assert detect_employment_type("Befristet") == "temporary"
    assert detect_employment_type("Something unclear") is None


def run_all() -> None:
    test_normalize_text_and_missing_fields()
    test_german_job_normalization()
    test_english_job_normalization()
    test_mixed_language_job_detection()
    test_location_normalization()
    test_url_normalization()
    test_date_normalization()
    test_german_b2_and_c1_detection()
    test_english_requirement_detection()
    test_junior_and_senior_detection()
    test_remote_and_hybrid_detection()
    test_employment_type_normalization()
    print("Normalization tests passed.")


if __name__ == "__main__":
    run_all()
