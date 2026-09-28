"""Profile-based relevance scoring for normalized jobs.

Candidate match scoring is separate from discovery relevance (see role_classifier).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config.role_taxonomy import canonicalize_filter_group
from app.config.scoring_profile import CEFR_RANK, cefr_at_most
from app.services.candidate_profile import load_profile
from app.services.role_classifier import classify_job, detect_role_category
from app.services.skills import compare_skills, extract_skills, normalize_skill_list
from app.sources.normalized_job import NormalizedJob

# Calibrated bands (also used by /stats and frontend filters).
CATEGORY_LABELS = {
    "Mükemmel Eşleşme": (90, 100),
    "Çok Uygun": (80, 89),
    "Uygun": (70, 79),
    "Olası": (55, 69),
    "Düşük Uygunluk": (0, 54),
}

# Keep legacy German labels mapped for older rows during transition.
LEGACY_CATEGORY_MAP = {
    "Sehr passend": "Çok Uygun",
    "Gut passend": "Uygun",
    "Möglich": "Olası",
    "Weniger passend": "Düşük Uygunluk",
}

DEGREE_PATTERN = re.compile(
    r"\b("
    r"informatik|computer\s*science|computer\s*engineering|"
    r"software\s*engineering|information\s*technology|"
    r"wirtschaftsinformatik|information\s*systems|"
    r"bilgisayar\s*mühendisliği|yazılım\s*mühendisliği"
    r")\b",
    re.IGNORECASE,
)

PROGRAM_PATTERN = re.compile(
    r"\b("
    r"graduate\s+program|trainee[\s-]?programm|trainee\s+program|"
    r"absolventenprogramm|ausbildungsprogramm\s+it"
    r")\b",
    re.IGNORECASE,
)

MANAGEMENT_PATTERN = re.compile(
    r"\b("
    r"personalverantwortung|mitarbeiterführung|teamleitung|"
    r"people\s+management|line\s+management|führungsverantwortung|"
    r"team\s+lead(?:er)?\b|engineering\s+manager"
    r")\b",
    re.IGNORECASE,
)

ENTRY_LEVEL_PATTERN = re.compile(
    r"\b("
    r"junior|berufseinsteiger|absolvent(?:en|in|innen)?|"
    r"graduate(?!\s+program)|entry[\s-]?level|einstiegsposition|"
    r"berufseinstieg|trainee"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class ScoreResult:
    score: int
    category: str
    positive_reasons: List[str] = field(default_factory=list)
    negative_reasons: List[str] = field(default_factory=list)
    role_category: str = "other"
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "category": self.category,
            "positive_reasons": list(self.positive_reasons),
            "negative_reasons": list(self.negative_reasons),
            "role_category": self.role_category,
            "matched_skills": list(self.matched_skills),
            "missing_skills": list(self.missing_skills),
        }


def score_category(score: int) -> str:
    if score >= 90:
        return "Mükemmel Eşleşme"
    if score >= 80:
        return "Çok Uygun"
    if score >= 70:
        return "Uygun"
    if score >= 55:
        return "Olası"
    return "Düşük Uygunluk"


def parse_language_requirement(stored: Optional[str]) -> Tuple[Optional[str], str]:
    """Parse 'B2|required' storage format."""
    if not stored:
        return None, "unknown"
    parts = stored.split("|", 1)
    if len(parts) != 2:
        return None, "unknown"
    level = None if parts[0] in {"", "null", "none"} else parts[0].upper()
    status = parts[1] or "unknown"
    return level, status


def parse_required_years(text: str) -> Optional[Tuple[Optional[int], Optional[int], str]]:
    """Return (min_years, max_years, kind) where kind is range|minimum|exact."""
    haystack = text.casefold().replace("–", "-").replace("—", "-")

    patterns = (
        (r"\b(0)\s*-\s*(2)\s*(?:years?|jahre(?:n)?)\b", "range"),
        (r"\b(0)\s*-\s*(1)\s*(?:years?|jahre(?:n)?)\b", "range"),
        (r"\b(1)\s*-\s*(2)\s*(?:years?|jahre(?:n)?)\b", "range"),
        (r"\b(1)\s*-\s*(3)\s*(?:years?|jahre(?:n)?)\b", "range"),
        (r"\b(2)\s*-\s*(3)\s*(?:years?|jahre(?:n)?)\b", "range"),
        (r"\b(2)\s*(?:years?|jahre(?:n)?)(?:\s+berufserfahrung)?\b", "exact"),
        (r"(?:mindestens|at\s+least|min\.?)\s*(3)\s*(?:years?|jahre(?:n)?)", "minimum"),
        (r"(?:mindestens|at\s+least|min\.?)\s*(4)\s*(?:years?|jahre(?:n)?)", "minimum"),
        (r"(?:mindestens|at\s+least|min\.?)\s*(5)\s*(?:years?|jahre(?:n)?)", "minimum"),
        (r"\b(3)\s*\+\s*(?:years?|jahre(?:n)?)\b", "minimum"),
        (r"\b(4)\s*\+\s*(?:years?|jahre(?:n)?)\b", "minimum"),
        (r"\b(5)\s*\+\s*(?:years?|jahre(?:n)?)\b", "minimum"),
        (r"\b(6)\s*\+\s*(?:years?|jahre(?:n)?)\b", "minimum"),
        (r"\b(3)\s*(?:years?|jahre(?:n)?)(?:\s+berufserfahrung)?\b", "exact"),
        (r"\b(4)\s*(?:years?|jahre(?:n)?)(?:\s+berufserfahrung)?\b", "exact"),
        (r"\b(5)\s*(?:years?|jahre(?:n)?)(?:\s+berufserfahrung)?\b", "exact"),
    )

    for pattern, kind in patterns:
        match = re.search(pattern, haystack)
        if not match:
            continue
        nums = [int(group) for group in match.groups() if group is not None]
        if kind == "range" and len(nums) >= 2:
            return nums[0], nums[1], kind
        if kind == "minimum" and nums:
            return nums[0], None, kind
        if kind == "exact" and nums:
            return nums[0], nums[0], kind
    return None


def score_job(
    job: NormalizedJob,
    profile: Optional[Dict[str, Any]] = None,
) -> ScoreResult:
    """
    Score against the local candidate profile.

    Missing job information is NEUTRAL (no bonus for absence).
    """
    profile = profile or load_profile()
    text = f"{job.title}\n{job.description}"
    title = job.title or ""
    title_l = title.casefold()
    text_l = text.casefold()

    classification = classify_job(title, job.description or "")
    role_category = detect_role_category(title, job.description or "")
    positive: List[str] = []
    negative: List[str] = []

    # Lower base than before so 100 is rare.
    score = 20

    target_categories = {
        canonicalize_filter_group(str(item))
        for item in (profile.get("target_categories") or [])
    }
    target_roles = [str(role) for role in (profile.get("target_roles") or [])]
    unwanted = [str(role) for role in (profile.get("unwanted_roles") or [])]
    preferred_max = int(profile.get("preferred_max_experience_years") or 2)
    preferred_models = set(profile.get("preferred_work_models") or [])
    preferred_locations = [str(loc) for loc in (profile.get("preferred_locations") or [])]
    profile_skills = normalize_skill_list(profile.get("skills") or [])
    candidate_german = str(profile.get("german_level") or "unknown").upper()
    candidate_english = str(profile.get("english_level") or "unknown").upper()
    education = str(profile.get("education") or "")
    role_group = canonicalize_filter_group(role_category)

    # 1) Target category / discovery family
    if role_group in target_categories or role_category in (profile.get("target_categories") or []):
        score += 18
        positive.append("Hedef pozisyon alanıyla eşleşiyor")
    elif classification.discovery_relevance in {"high", "medium"} and role_category != "other":
        # Keep broad technical roles discoverable; mild mismatch only.
        score -= 4
        negative.append("Hedef alanların dışında / yakın teknik alan")
    elif role_category != "other":
        score -= 12
        negative.append("Rolle außerhalb der Zielbereiche")

    # 2) Target title overlap
    title_hit = False
    for role in target_roles:
        role_l = role.casefold().strip()
        if len(role_l) >= 4 and role_l in title_l:
            score += 10
            positive.append("Hedef unvanla örtüşüyor")
            title_hit = True
            break
    category_targeted = role_group in target_categories or role_category in (
        profile.get("target_categories") or []
    )
    if not title_hit and ENTRY_LEVEL_PATTERN.search(title) and category_targeted:
        score += 4  # mild junior signal only when category already matches

    # Unwanted / seniority — multi-level titles with junior keep the job scoreable
    unwanted_hit = any(token.casefold() in title_l for token in unwanted if len(token.strip()) >= 3)
    seniority = _detect_seniority_penalty(
        title,
        text,
        job.experience_level,
        available_levels=classification.available_levels,
    )
    if unwanted_hit and not (
        "junior" in classification.available_levels
        or "intern" in classification.available_levels
    ):
        score -= 22
        negative.append("İstenmeyen / üst seviye pozisyon")
    elif seniority:
        score += seniority[0]  # already negative
        negative.append(seniority[1])

    # 3) Skills
    job_skills = extract_skills(text)
    matched, missing = compare_skills(job_skills, profile_skills)
    if matched:
        # Cap skill bonus so skill spam cannot force 100.
        bonus = min(24, 4 * len(matched))
        score += bonus
        for skill in matched[:6]:
            positive.append(f"{skill} eşleşiyor")
    if missing:
        # Missing skills are warnings; mild penalty only when many required skills absent.
        if len(missing) >= 4 and len(matched) == 0:
            score -= 8
        for skill in missing[:5]:
            negative.append(f"{skill} profilinde bulunmuyor")

    # 4) Education relevance (only if job mentions a degree field)
    if DEGREE_PATTERN.search(text):
        edu_l = education.casefold()
        if any(token in edu_l for token in ("informatik", "computer", "software", "engineering")):
            score += 6
            positive.append("Eğitim alanı ilgili")
        # If education empty → neutral

    # 5) Experience vs preferred max
    years = parse_required_years(text)
    if years:
        min_y, max_y, kind = years
        required = min_y if min_y is not None else 0
        if kind == "range" and max_y is not None:
            required = max_y
        if required <= preferred_max:
            score += 10
            positive.append("Deneyim beklentisi uygun")
        elif required == preferred_max + 1:
            score -= 6
            negative.append(f"{required} yıl deneyim tercih ediliyor")
        elif required == preferred_max + 2:
            score -= 12
            negative.append(f"{required} yıl deneyim tercih ediliyor")
        else:
            score -= 20
            negative.append(f"{required}+ yıl deneyim gerekli")
    elif job.experience_level in {"junior", "entry_level", "internship"}:
        score += 6
        positive.append("Junior / Berufseinsteiger")
    # missing years info → neutral

    if PROGRAM_PATTERN.search(text):
        score += 3
        positive.append("Trainee- / Graduate-Programm")

    # 6/7) Languages — compare against profile; German-language ad alone is NOT a penalty
    de_level, de_status = parse_language_requirement(job.german_requirement)
    if de_status == "required" and de_level:
        if candidate_german in CEFR_RANK and de_level in CEFR_RANK:
            if CEFR_RANK[candidate_german] >= CEFR_RANK[de_level]:
                score += 8
                positive.append("Almanca seviyesi yeterli")
            else:
                gap = CEFR_RANK[de_level] - CEFR_RANK[candidate_german]
                score -= 8 if gap == 1 else 16
                negative.append(f"Almanca {de_level} gerekiyor")
        # unknown candidate level → neutral
    elif de_status == "preferred" and de_level and candidate_german in CEFR_RANK:
        if cefr_at_most(de_level, candidate_german) or CEFR_RANK.get(candidate_german, 0) >= CEFR_RANK.get(de_level, 0):
            score += 4
            positive.append(f"Deutsch {de_level} yeterli / tercih")

    en_level, en_status = parse_language_requirement(job.english_requirement)
    if en_status in {"required", "preferred"}:
        if candidate_english in CEFR_RANK:
            score += 6
            positive.append("İngilizce kabul ediliyor / uyumlu")
        # if candidate english unknown → neutral

    # 8) Work model
    if job.remote and "remote" in preferred_models:
        score += 6
        positive.append("Remote çalışma tercihine uygun")
    elif job.hybrid and "hybrid" in preferred_models:
        score += 6
        positive.append("Hibrit çalışma tercihine uygun")
    elif (not job.remote and not job.hybrid) and "onsite" in preferred_models:
        score += 3
        positive.append("Ofis çalışması tercihine uygun")
    # unknown/mismatch → neutral (no auto penalty)

    # 9) Preferred locations (mild)
    location_l = (job.location or "").casefold()
    if preferred_locations and location_l:
        if any(loc.casefold() in location_l or location_l in loc.casefold() for loc in preferred_locations if loc.strip()):
            score += 4
            positive.append("Tercih edilen lokasyonla uyumlu")

    # 10) Management responsibility
    if MANAGEMENT_PATTERN.search(text):
        score -= 12
        negative.append("Führungsverantwortung gefordert")

    score = max(0, min(100, score))
    # Perfect score requires strong multi-factor fit
    if score >= 95 and (len(matched) < 3 or role_group not in target_categories):
        score = min(score, 92)

    return ScoreResult(
        score=score,
        category=score_category(score),
        positive_reasons=_unique(positive),
        negative_reasons=_unique(negative),
        role_category=role_category,
        matched_skills=matched,
        missing_skills=missing,
    )


def apply_score(
    job: NormalizedJob,
    profile: Optional[Dict[str, Any]] = None,
) -> ScoreResult:
    """Score a job and write match_score / match_category onto it."""
    result = score_job(job, profile=profile)
    classification = classify_job(job.title or "", job.description or "")
    job.match_score = result.score
    job.match_category = result.category
    job.raw = dict(job.raw or {})
    job.raw["match_reasons"] = {
        "positive_reasons": result.positive_reasons,
        "negative_reasons": result.negative_reasons,
        "role_category": result.role_category,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
    }
    job.raw["classification"] = classification.to_dict()
    job.raw["discovery_relevance"] = classification.discovery_relevance
    job.raw["role_family"] = classification.primary_role_family
    return result


def _detect_seniority_penalty(
    title: str,
    text: str,
    experience_level: Optional[str],
    available_levels: Optional[Sequence[str]] = None,
) -> Optional[Tuple[int, str]]:
    title_l = title.casefold()
    text_l = text.casefold()
    levels = set(available_levels or [])

    # Mixed junior/specialist/senior postings remain applicable for juniors.
    if "junior" in levels or "intern" in levels:
        return None

    if experience_level == "lead" or re.search(
        r"\b(lead|principal|staff\s+engineer|staff\s+software)\b", title_l
    ):
        return -22, "Lead-/Principal-Niveau"
    if experience_level == "senior" or (
        re.search(r"\bsenior\b", title_l) and "specialist" not in levels
    ):
        return -22, "Senior-Niveau"
    if (
        "senior" in levels
        and "specialist" not in levels
        and "mid" not in levels
    ):
        return -22, "Senior-Niveau"
    if re.search(r"\b(senior|principal)\b", text_l) and re.search(
        r"\b(required|erforderlich|zwingend|mandatory)\b", text_l
    ):
        # Only when junior path is not offered.
        if "junior" not in levels:
            return -18, "Senior-Niveau"
    return None


def _unique(items: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
