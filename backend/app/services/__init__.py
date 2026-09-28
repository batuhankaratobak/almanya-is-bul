"""Business logic services (scoring, normalization, duplicates)."""

from app.services.deduplication import (
    DedupResult,
    build_fingerprint,
    list_source_links,
    upsert_normalized_job,
)
from app.services.normalization import (
    LanguageRequirement,
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
from app.services.scoring import ScoreResult, apply_score, detect_role_category, score_job

__all__ = [
    "DedupResult",
    "LanguageRequirement",
    "ScoreResult",
    "apply_score",
    "build_fingerprint",
    "detect_employment_type",
    "detect_english_requirement",
    "detect_experience_level",
    "detect_german_requirement",
    "detect_job_language",
    "detect_role_category",
    "detect_work_model",
    "list_source_links",
    "normalize_arbeitsagentur_job",
    "normalize_arbeitnow_job",
    "normalize_germantechjobs_job",
    "normalize_location",
    "normalize_raw_job",
    "normalize_text",
    "normalize_url",
    "parse_date",
    "score_job",
    "upsert_normalized_job",
]
