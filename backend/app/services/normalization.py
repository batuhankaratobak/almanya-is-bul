"""Normalize raw source job payloads into NormalizedJob."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from dateutil import parser as date_parser

from app.models.status import ApplicationStatus
from app.sources.normalized_job import NormalizedJob

_WHITESPACE_RE = re.compile(r"\s+")

GERMAN_INDICATORS = (
    "und",
    "oder",
    "wir",
    "sie",
    "kenntnisse",
    "erfahrung",
    "aufgaben",
    "anforderungen",
    "bewerbung",
    "deutsch",
    "berufserfahrung",
    "unternehmen",
    "stellenbeschreibung",
)

ENGLISH_INDICATORS = (
    "and",
    "or",
    "we",
    "you",
    "requirements",
    "experience",
    "responsibilities",
    "skills",
    "apply",
    "english",
    "company",
    "job description",
)

_CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


@dataclass(frozen=True)
class LanguageRequirement:
    level: Optional[str]
    status: str  # required | preferred | not_required | unknown

    def to_storage(self) -> str:
        return f"{self.level or 'null'}|{self.status}"


def normalize_text(value: Any) -> str:
    """Trim and collapse whitespace; preserve readable capitalization."""
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").strip()
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text)


def normalize_location(value: Any) -> Tuple[str, str]:
    """
    Return (display_location, comparison_key).

    Keeps the display form human-readable; comparison key lowercases and
    strips common country suffixes for duplicate checks later.
    """
    display = normalize_text(value)
    if not display:
        return "", ""

    key = display.casefold()
    for suffix in (
        ", germany",
        ", deutschland",
        ", de",
        " germany",
        " deutschland",
    ):
        if key.endswith(suffix):
            key = key[: -len(suffix)].rstrip(" ,")
            break
    if key.endswith(" de") and len(key) > 3:
        key = key[:-3].rstrip(" ,")
    key = _WHITESPACE_RE.sub(" ", key).strip(" ,")
    return display, key


def normalize_url(value: Any) -> str:
    """Trim URL; return empty string for clearly invalid/empty values."""
    url = normalize_text(value)
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def parse_date(value: Any) -> Optional[datetime]:
    """Parse common date formats into timezone-aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        # Treat large numbers as unix timestamps (seconds).
        timestamp = float(value)
        if timestamp > 1_000_000_000_000:
            timestamp /= 1000.0
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = normalize_text(value)
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(text[:19] if "T" in text and fmt.endswith("%S") else text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = date_parser.parse(text, dayfirst=True, fuzzy=False)
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def detect_job_language(title: str, description: str) -> str:
    """Deterministic de / en / de/en / unknown detection from title + description."""
    text = f"{title} {description}".casefold()
    if not text.strip():
        return "unknown"

    german_hits = sum(1 for word in GERMAN_INDICATORS if _contains_word(text, word))
    english_hits = sum(1 for word in ENGLISH_INDICATORS if _contains_word(text, word))

    if german_hits >= 2 and english_hits >= 2:
        return "de/en"
    if german_hits > english_hits and german_hits >= 2:
        return "de"
    if english_hits > german_hits and english_hits >= 2:
        return "en"
    if german_hits >= 1 and english_hits >= 1:
        return "de/en"
    if german_hits >= 1:
        return "de"
    if english_hits >= 1:
        return "en"
    return "unknown"


def detect_german_requirement(text: str) -> LanguageRequirement:
    return _detect_language_requirement(text, language="de")


def detect_english_requirement(text: str) -> LanguageRequirement:
    return _detect_language_requirement(text, language="en")


def detect_experience_level(text: str) -> str:
    """Return internship|entry_level|junior|mid|senior|lead|unknown."""
    haystack = text.casefold()
    if not haystack.strip():
        return "unknown"

    if re.search(r"\b(principal|staff)\b", haystack):
        return "lead"
    if re.search(r"\blead\b", haystack) and not re.search(r"\bleadership training\b", haystack):
        return "lead"
    if re.search(
        r"\b(senior|5\+\s*years?|6\+\s*years?|mehrjährige\s+berufserfahrung|"
        r"mindestens\s*5\s*jahre|at least\s*5\s*years)\b",
        haystack,
    ):
        return "senior"
    if re.search(r"\b(praktikum|internship|intern)\b", haystack):
        return "internship"
    if re.search(
        r"\b(berufseinsteiger|absolvent(?:en|in|innen)?|graduate(?:\s+program)?|"
        r"entry[\s-]?level|0\s*[-–]\s*1\s*years?|0\s*[-–]\s*2\s*years?|"
        r"1\s*[-–]\s*2\s*years?|\b1\s*year\b)\b",
        haystack,
    ):
        return "entry_level"
    if re.search(r"\bjunior\b", haystack):
        return "junior"
    if re.search(r"\b(mid[\s-]?level|3\s*[-–]\s*5\s*years?)\b", haystack):
        return "mid"
    return "unknown"


def detect_work_model(text: str) -> Tuple[bool, bool]:
    """
    Detect remote/hybrid from work-model phrases.

    Avoids treating unrelated 'remote' mentions as remote work.
    """
    haystack = text.casefold()
    hybrid = bool(
        re.search(
            r"\b(hybrid(?:es)?(?:\s+arbeiten|\s+work)?|teilweise\s+home\s*-?\s*office|"
            r"hybrid\s*\/\s*remote)\b",
            haystack,
        )
    )
    remote = bool(
        re.search(
            r"\b("
            r"100%\s*remote|fully\s+remote|remote\s*(?:work|position|job|rolle|stelle)|"
            r"arbeiten\s+remote|remote\s+arbeiten|"
            r"home\s*-?\s*office(?:\s*möglich)?|"
            r"reines?\s+home\s*-?\s*office"
            r")\b",
            haystack,
        )
    )
    # Bare "remote" only when it looks like a work model label.
    if not remote and re.search(r"(?:^|[\n•|\-:/])\s*remote\s*(?:$|[\n•|,])", haystack):
        remote = True
    if hybrid and remote and re.search(r"\bhybrid\b", haystack):
        # Hybrid postings often mention homeoffice; keep both when both are clear.
        pass
    return remote, hybrid


def detect_employment_type(text: str) -> Optional[str]:
    haystack = text.casefold()
    if not haystack.strip():
        return None
    patterns = (
        (r"\b(werkstudent(?:in)?|working[\s_-]*student)\b", "working_student"),
        (r"\b(praktikum|internship)\b", "internship"),
        (r"\b(ausbildung|apprenticeship)\b", "apprenticeship"),
        (r"\b(teilzeit|part[\s_-]?time)\b", "part_time"),
        (r"\b(befristet|temporary|fixed[\s_-]?term)\b", "temporary"),
        (r"\b(vollzeit|full[\s_-]?time|permanent|unbefristet)\b", "full_time"),
    )
    for pattern, value in patterns:
        if re.search(pattern, haystack):
            return value
    return None


def normalize_raw_job(raw: Dict[str, Any], *, source: str) -> NormalizedJob:
    """Normalize a generic raw dictionary into NormalizedJob."""
    title = normalize_text(raw.get("title") or raw.get("position") or raw.get("name"))
    company = normalize_text(raw.get("company") or raw.get("company_name") or raw.get("employer"))
    location_display, location_key = normalize_location(
        raw.get("location") or raw.get("city") or raw.get("arbeitsort")
    )
    # Keep original description text unchanged aside from None-safety.
    description = "" if raw.get("description") is None else str(raw.get("description"))
    job_url = normalize_url(raw.get("job_url") or raw.get("url") or raw.get("link"))
    source_job_id = normalize_text(raw.get("source_job_id") or raw.get("id") or raw.get("external_id")) or None
    date_posted = parse_date(raw.get("date_posted") or raw.get("created_at") or raw.get("published_at"))

    combined = f"{title}\n{description}\n{normalize_text(raw.get('employment_type'))}"
    job_language = detect_job_language(title, description)
    german_req = detect_german_requirement(combined)
    english_req = detect_english_requirement(combined)
    experience_level = detect_experience_level(f"{title}\n{description}")
    remote, hybrid = detect_work_model(combined)

    employment_type = detect_employment_type(
        normalize_text(raw.get("employment_type")) or combined
    )

    country = normalize_text(raw.get("country") or "DE").upper() or "DE"
    if len(country) > 8:
        country = country[:8]
    application_url = normalize_url(
        raw.get("application_url") or raw.get("redirect_url") or job_url
    )

    now = datetime.now(timezone.utc)
    job = NormalizedJob(
        source=source,
        source_job_id=source_job_id,
        title=title,
        company=company,
        location=location_display,
        location_normalized=location_key,
        country=country,
        description=description,
        job_url=job_url,
        application_url=application_url or job_url,
        date_posted=date_posted,
        first_seen_at=now,
        last_seen_at=now,
        remote=remote,
        hybrid=hybrid,
        employment_type=employment_type,
        job_language=job_language,
        german_requirement=german_req.to_storage(),
        english_requirement=english_req.to_storage(),
        experience_level=experience_level,
        match_score=0,
        match_category=None,
        status=ApplicationStatus.NEW.value,
        raw=dict(raw),
    )
    # Phase 6: attach deterministic match score/category.
    from app.services.scoring import apply_score

    apply_score(job)
    return job


def normalize_arbeitsagentur_job(raw: Dict[str, Any]) -> NormalizedJob:
    """Map Arbeitsagentur-like raw fields into NormalizedJob."""
    location = raw.get("arbeitsort") or raw.get("location")
    if isinstance(location, dict):
        location = location.get("ort") or ""

    mapped = {
        "source_job_id": raw.get("referenznummer") or raw.get("id") or raw.get("refnr"),
        "title": raw.get("titel")
        or raw.get("stellenangebotsTitel")
        or raw.get("title"),
        "company": raw.get("arbeitgeber") or raw.get("firma") or raw.get("company"),
        "location": location,
        "description": raw.get("stellenbeschreibung")
        or raw.get("stellenangebotsBeschreibung")
        or raw.get("description")
        or "",
        "job_url": raw.get("externeUrl")
        or raw.get("externeURL")
        or raw.get("job_url")
        or raw.get("url"),
        "date_posted": raw.get("eintrittsdatum")
        or raw.get("aktuelleVeroeffentlichungsdatum")
        or raw.get("datumErsteVeroeffentlichung")
        or raw.get("date_posted"),
        "employment_type": raw.get("arbeitszeit") or raw.get("employment_type"),
    }
    job = normalize_raw_job(mapped, source="Arbeitsagentur")
    if raw.get("homeofficemoeglich") is True and not job.remote and not job.hybrid:
        job.hybrid = True
    return job


def normalize_arbeitnow_job(raw: Dict[str, Any]) -> NormalizedJob:
    """Map Arbeitnow-like raw fields into NormalizedJob."""
    # Keep original description unchanged (do not append tags).
    description = "" if raw.get("description") is None else str(raw.get("description"))
    mapped = {
        "source_job_id": raw.get("slug") or raw.get("source_job_id") or raw.get("id"),
        "title": raw.get("title"),
        "company": raw.get("company_name") or raw.get("company"),
        "location": raw.get("location"),
        "description": description,
        "job_url": raw.get("url") or raw.get("job_url"),
        "date_posted": raw.get("created_at") or raw.get("date_posted"),
        "employment_type": (
            raw.get("job_types")[0]
            if isinstance(raw.get("job_types"), list) and raw.get("job_types")
            else raw.get("employment_type")
        ),
    }
    # Prefer explicit remote flag from Arbeitnow when present.
    job = normalize_raw_job(mapped, source="Arbeitnow")
    if raw.get("remote") is True and not job.remote:
        job.remote = True
        from app.services.scoring import apply_score

        apply_score(job)
    return job


def normalize_germantechjobs_job(raw: Dict[str, Any]) -> NormalizedJob:
    """Map GermanTechJobs-like raw fields into NormalizedJob."""
    mapped = {
        "source_job_id": str(raw.get("id")) if raw.get("id") is not None else raw.get("slug"),
        "title": raw.get("title") or raw.get("position"),
        "company": (raw.get("company") or {}).get("name")
        if isinstance(raw.get("company"), dict)
        else raw.get("company"),
        "location": raw.get("city") or raw.get("location"),
        "description": raw.get("description") or raw.get("excerpt") or "",
        "job_url": raw.get("url") or raw.get("link") or raw.get("job_url"),
        "date_posted": raw.get("postedAt") or raw.get("createdAt") or raw.get("date_posted"),
        "employment_type": raw.get("employmentType") or raw.get("employment_type"),
    }
    job = normalize_raw_job(mapped, source="GermanTechJobs")
    work_model = normalize_text(raw.get("workModel") or raw.get("work_model")).casefold()
    changed = False
    if "hybrid" in work_model:
        job.hybrid = True
        changed = True
    if work_model in {"remote", "fully remote"} or "remote" in work_model:
        job.remote = True
        changed = True
    if changed:
        from app.services.scoring import apply_score

        apply_score(job)
    return job


def normalize_absolventa_job(raw: Dict[str, Any]) -> NormalizedJob:
    """Map Absolventa JobPosting fields into NormalizedJob."""
    mapped = {
        "source_job_id": raw.get("source_job_id") or raw.get("id"),
        "title": raw.get("title"),
        "company": raw.get("company") or raw.get("company_name"),
        "location": raw.get("location"),
        "description": "" if raw.get("description") is None else str(raw.get("description")),
        "job_url": raw.get("job_url") or raw.get("url"),
        "date_posted": raw.get("date_posted") or raw.get("datePosted"),
        "employment_type": raw.get("employment_type") or raw.get("employmentType"),
    }
    return normalize_raw_job(mapped, source="Absolventa")


def normalize_eures_job(raw: Dict[str, Any]) -> NormalizedJob:
    """Map EURES search/detail fields into NormalizedJob."""
    mapped = {
        "source_job_id": raw.get("source_job_id") or raw.get("id") or raw.get("reference"),
        "title": raw.get("title"),
        "company": raw.get("company")
        or (
            (raw.get("employer") or {}).get("name")
            if isinstance(raw.get("employer"), dict)
            else None
        ),
        "location": raw.get("location"),
        "description": "" if raw.get("description") is None else str(raw.get("description")),
        "job_url": raw.get("job_url") or raw.get("url"),
        "date_posted": raw.get("date_posted") or raw.get("creationDate"),
        "employment_type": raw.get("employment_type"),
    }
    return normalize_raw_job(mapped, source="EURES")


def _detect_language_requirement(text: str, *, language: str) -> LanguageRequirement:
    haystack = text.casefold()
    if not haystack.strip():
        return LanguageRequirement(level=None, status="unknown")

    if language == "de":
        lang_patterns = (
            r"deutsch(?:kenntnisse)?",
            r"german(?:\s+language)?",
        )
        not_required_patterns = (
            r"deutsch\s+(?:nicht\s+erforderlich|optional)",
            r"no\s+german\s+required",
            r"german\s+not\s+required",
        )
        preferred_patterns = (
            r"deutsch(?:kenntnisse)?\s+(?:von\s+vorteil|wünschenswert)",
            r"german\s+(?:is\s+)?(?:preferred|a\s+plus|nice\s+to\s+have)",
        )
        required_patterns = (
            r"deutsch\s+erforderlich",
            r"(?:flie[sß]ende|sehr\s+gute)\s+deutschkenntnisse",
            r"german\s+required",
            r"fluent\s+german",
        )
    else:
        lang_patterns = (
            r"englisch(?:kenntnisse)?",
            r"english(?:\s+language)?",
        )
        not_required_patterns = (
            r"englisch\s+(?:nicht\s+erforderlich|optional)",
            r"english\s+not\s+required",
            r"no\s+english\s+required",
        )
        preferred_patterns = (
            r"englisch\s+(?:von\s+vorteil|wünschenswert)",
            r"english\s+(?:preferred|a\s+plus|nice\s+to\s+have)",
            r"good\s+command\s+of\s+english",
        )
        required_patterns = (
            r"englisch\s+erforderlich",
            r"(?:flie[sß]ende|sehr\s+gute)\s+englischkenntnisse",
            r"english\s+required",
            r"fluent\s+english",
        )

    mentioned = any(re.search(pattern, haystack) for pattern in lang_patterns)
    level = _extract_cefr_level(haystack, language=language)

    if any(re.search(pattern, haystack) for pattern in not_required_patterns):
        return LanguageRequirement(level=level, status="not_required")
    if any(re.search(pattern, haystack) for pattern in required_patterns):
        return LanguageRequirement(level=level, status="required")
    if any(re.search(pattern, haystack) for pattern in preferred_patterns):
        return LanguageRequirement(level=level, status="preferred")
    if level is not None and mentioned:
        # Explicit CEFR for that language ⇒ treat as required unless marked preferred.
        return LanguageRequirement(level=level, status="required")
    if mentioned:
        return LanguageRequirement(level=level, status="unknown")
    return LanguageRequirement(level=None, status="unknown")


def _extract_cefr_level(haystack: str, *, language: str) -> Optional[str]:
    lang = "deutsch|german" if language == "de" else "englisch|english"
    for level in _CEFR_LEVELS:
        escaped = re.escape(level)
        patterns = (
            rf"(?:{lang})(?:kenntnisse)?[^\.\n]{{0,40}}\b{escaped}\b",
            rf"\b{escaped}\b[^\.\n]{{0,40}}(?:{lang})",
        )
        for pattern in patterns:
            if re.search(pattern, haystack, flags=re.IGNORECASE):
                return level
    return None


def _contains_word(text: str, word: str) -> bool:
    if " " in word:
        return word in text
    return re.search(rf"\b{re.escape(word)}\b", text) is not None
