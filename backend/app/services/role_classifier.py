"""Broad role classification: discovery relevance vs candidate match scoring.

Collect broadly → classify → analyze → score → rank.
Missing/unknown information is neutral. Unrelated roles get low discovery.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config.role_taxonomy import (
    ANALYTICAL_TECH_SIGNALS,
    EDUCATION_COMPATIBLE_TERMS,
    GENERIC_ENGINEERING_TITLE_SIGNALS,
    MANUFACTURING_QA_SIGNALS,
    ROLE_FAMILIES,
    TECH_RESPONSIBILITY_SIGNALS,
    UNRELATED_ENGINEERING_SIGNALS,
    RoleFamily,
    all_title_terms,
    canonicalize_filter_group,
)


LEVEL_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("intern", r"\b(intern|internship|praktikant(?:in)?|stajyer)\b"),
    ("junior", r"\b(junior|berufseinsteiger|entry[\s-]?level|einstieg|graduate|absolvent(?:in)?)\b"),
    ("specialist", r"\b(specialist|spezialist(?:in)?|uzman(?:ı)?)\b"),
    ("mid", r"\b(mid[\s-]?level|intermediate|mittlere[rn]?\s+erfahrung)\b"),
    ("senior", r"\b(senior|principal|staff|lead)\b"),
)


@dataclass
class ClassificationResult:
    primary_role_family: str
    secondary_role_families: List[str] = field(default_factory=list)
    filter_group: str = "other_technical"
    discovery_relevance: str = "low"  # high | medium | low
    detected_seniority: Optional[str] = None
    available_levels: List[str] = field(default_factory=list)
    detected_skills: List[str] = field(default_factory=list)
    detected_responsibilities: List[str] = field(default_factory=list)
    education_compatibility: str = "unknown"  # compatible | related | unknown | incompatible
    classification_reasons: List[str] = field(default_factory=list)
    family_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def classify_job(
    title: str,
    description: str = "",
    *,
    extra_text: str = "",
) -> ClassificationResult:
    """Classify a job using title + description + responsibility/skill signals."""
    title = title or ""
    description = description or ""
    title_l = title.casefold()
    desc_l = description.casefold()
    extra_l = (extra_text or "").casefold()
    full_l = _strip_negated_tech_phrases(f"{title_l}\n{desc_l}\n{extra_l}")
    desc_l = _strip_negated_tech_phrases(desc_l)

    available_levels = detect_available_levels(title, description)
    detected_seniority = _primary_seniority(available_levels, title_l)
    education = detect_education_compatibility(full_l)

    family_scores: Dict[str, float] = {}
    family_hits: Dict[str, Dict[str, List[str]]] = {}

    for family in ROLE_FAMILIES:
        if not family.enabled:
            continue
        score, hits = _score_family(family, title_l, desc_l, full_l)
        if score > 0:
            family_scores[family.id] = score
            family_hits[family.id] = hits

    # Language-specific developer/engineer titles (e.g. Senior Java Developer).
    _boost_language_developer_titles(title_l, full_l, family_scores, family_hits)

    # Broad engineering discovery boost / unrelated demotion.
    unrelated = _contains_any(full_l, UNRELATED_ENGINEERING_SIGNALS) or _is_clearly_non_it_engineering(
        title_l, full_l
    )
    tech_signals = _find_terms(full_l, TECH_RESPONSIBILITY_SIGNALS)
    analytical_tech = _find_terms(full_l, ANALYTICAL_TECH_SIGNALS)
    generic_eng = _contains_any(title_l, GENERIC_ENGINEERING_TITLE_SIGNALS)
    title_is_software = bool(
        re.search(r"\b(software|informatik|developer|entwickler|devops|frontend|backend)\b", title_l)
    )

    if unrelated and (not tech_signals or not title_is_software) and not analytical_tech:
        return ClassificationResult(
            primary_role_family="unrelated_engineering",
            filter_group="other_technical",
            discovery_relevance="low",
            detected_seniority=detected_seniority,
            available_levels=available_levels,
            education_compatibility=education,
            classification_reasons=["Unrelated engineering / non-IT field"],
            family_scores=family_scores,
        )

    if generic_eng and tech_signals:
        # Boost best matching technical family or create other_technical discovery.
        if family_scores:
            top_id = max(family_scores, key=family_scores.get)
            family_scores[top_id] = family_scores[top_id] + 8
        else:
            family_scores["other_technical_discovery"] = 12
            family_hits["other_technical_discovery"] = {
                "titles": [title],
                "skills": [],
                "responsibilities": tech_signals[:6],
            }

    if not family_scores:
        # Analytical/finance titles without taxonomy title hit but with tech signals.
        if analytical_tech and _looks_analytical_title(title_l):
            family_scores["financial_analysis"] = 10
            family_hits["financial_analysis"] = {
                "titles": [],
                "skills": analytical_tech[:6],
                "responsibilities": analytical_tech[:6],
            }
        elif tech_signals:
            family_scores["other_technical_discovery"] = 8
            family_hits["other_technical_discovery"] = {
                "titles": [],
                "skills": [],
                "responsibilities": tech_signals[:6],
            }
        else:
            return ClassificationResult(
                primary_role_family="other",
                filter_group="other_technical",
                discovery_relevance="low",
                detected_seniority=detected_seniority,
                available_levels=available_levels,
                education_compatibility=education,
                classification_reasons=["No technical role signals"],
            )

    ranked = sorted(family_scores.items(), key=lambda item: item[1], reverse=True)
    primary_id = ranked[0][0]
    primary_score = ranked[0][1]
    secondary = [fid for fid, score in ranked[1:5] if score >= max(6.0, primary_score * 0.45)]

    primary_family = _resolve_family(primary_id)
    filter_group = (
        primary_family.filter_group
        if primary_family
        else ("other_technical" if primary_id.startswith("other_") else "other_technical")
    )

    # Manufacturing QA demotion when no software-test signals.
    if primary_id in {"software_testing", "test_automation", "validation"} or "quality engineer" in title_l:
        if _contains_any(full_l, MANUFACTURING_QA_SIGNALS) and not _has_software_qa_signals(full_l):
            return ClassificationResult(
                primary_role_family="manufacturing_quality",
                secondary_role_families=[],
                filter_group="other_technical",
                discovery_relevance="low",
                detected_seniority=detected_seniority,
                available_levels=available_levels,
                education_compatibility=education,
                classification_reasons=["Quality role appears manufacturing-focused, not software QA"],
                family_scores=family_scores,
            )

    # Analytical roles require tech signals for high/medium discovery.
    if filter_group in {"financial_analytics", "planning_performance", "supply_chain_analytics"}:
        if not analytical_tech and primary_score < 16:
            discovery = "low"
        elif analytical_tech:
            discovery = "high" if primary_score >= 14 or education == "compatible" else "medium"
        else:
            discovery = "medium"
    elif primary_id in {"process_analysis"} and primary_score < 14 and not tech_signals:
        discovery = "medium" if education == "compatible" else "low"
    else:
        discovery = _discovery_from_score(primary_score, primary_family)

    if unrelated and discovery == "high":
        discovery = "medium"
    if education == "compatible" and discovery == "medium" and primary_score >= 8:
        discovery = "high"

    hits = family_hits.get(primary_id, {"titles": [], "skills": [], "responsibilities": []})
    reasons = _build_reasons(primary_id, filter_group, discovery, hits, available_levels, education)

    detected_skills = _unique(hits.get("skills", []) + analytical_tech[:8])
    detected_resp = _unique(hits.get("responsibilities", []) + tech_signals[:8])

    return ClassificationResult(
        primary_role_family=primary_id,
        secondary_role_families=secondary,
        filter_group=filter_group,
        discovery_relevance=discovery,
        detected_seniority=detected_seniority,
        available_levels=available_levels,
        detected_skills=detected_skills,
        detected_responsibilities=detected_resp,
        education_compatibility=education,
        classification_reasons=reasons,
        family_scores=family_scores,
    )


def detect_role_category(title: str, description: str = "") -> str:
    """
    Backward-compatible category id for filters/scoring.

    Returns a UI filter-group id (including legacy aliases when appropriate).
    """
    result = classify_job(title, description)
    if result.discovery_relevance == "low" and result.primary_role_family in {
        "other",
        "unrelated_engineering",
        "manufacturing_quality",
    }:
        return "other"

    group = result.filter_group
    # Preserve legacy ids when they are a better semantic fit.
    family = _resolve_family(result.primary_role_family)
    if family:
        if family.id in {"system_administration"}:
            return "system_administration"
        if family.id in {"application_support"}:
            return "application_support"
        if family.id in {"it_consulting"}:
            return "it_consulting"
    return group


def is_discovery_keep(result: ClassificationResult) -> bool:
    return result.discovery_relevance in {"high", "medium"}


def detect_available_levels(title: str, description: str = "") -> List[str]:
    text = f"{title}\n{description}"
    # Prefer title for level lists like "Junior / Specialist / Senior Specialist"
    title_levels = [level for level, pattern in LEVEL_PATTERNS if re.search(pattern, title, re.I)]
    if title_levels:
        return _unique(title_levels)
    return _unique(
        [level for level, pattern in LEVEL_PATTERNS if re.search(pattern, text, re.I)]
    )


def detect_education_compatibility(text_l: str) -> str:
    if not text_l.strip():
        return "unknown"
    if _contains_any(text_l, EDUCATION_COMPATIBLE_TERMS):
        # Strong CS/CE markers
        strong = (
            "computer engineering",
            "computer science",
            "software engineering",
            "informatik",
            "wirtschaftsinformatik",
            "bilgisayar mühendisliği",
            "yazılım mühendisliği",
            "information technology",
            "information systems",
            "management information systems",
            "yönetim bilişim",
        )
        if _contains_any(text_l, strong):
            return "compatible"
        return "related"
    if _contains_any(text_l, ("accounting degree", "law degree", "medizin", "pflege", "rechtswissenschaften")):
        return "incompatible"
    return "unknown"


def job_matches_filter_category(
    title: str,
    description: str,
    category: str,
) -> bool:
    """True if job's filter group (or alias) matches requested category."""
    result = classify_job(title, description)
    if result.discovery_relevance == "low" and result.primary_role_family in {
        "other",
        "unrelated_engineering",
        "manufacturing_quality",
    }:
        return False
    requested = canonicalize_filter_group(category)
    actual = canonicalize_filter_group(result.filter_group)
    if requested == actual:
        return True
    # Legacy exact family-group ids
    if detect_role_category(title, description) == category:
        return True
    # Secondary families may belong to the requested group
    for fid in [result.primary_role_family, *result.secondary_role_families]:
        family = _resolve_family(fid)
        if family and canonicalize_filter_group(family.filter_group) == requested:
            return True
    return False


_LANGUAGE_DEV_MARKERS: Tuple[str, ...] = (
    "java",
    "python",
    "javascript",
    "typescript",
    "golang",
    "go developer",
    "c#",
    "c++",
    ".net",
    "php",
    "ruby",
    "kotlin",
    "swift",
    "scala",
    "rust",
)


def _boost_language_developer_titles(
    title_l: str,
    full_l: str,
    family_scores: Dict[str, float],
    family_hits: Dict[str, Dict[str, List[str]]],
) -> None:
    if not re.search(r"\b(developer|entwickler|engineer|software)\b", title_l):
        return
    lang_hits = [lang for lang in _LANGUAGE_DEV_MARKERS if lang in title_l or lang in full_l]
    if not lang_hits:
        return
    family_scores["software_engineering"] = family_scores.get("software_engineering", 0) + 16
    hits = family_hits.setdefault(
        "software_engineering",
        {"titles": [], "skills": [], "responsibilities": []},
    )
    hits["skills"] = _unique(list(hits.get("skills", [])) + lang_hits)[:10]
    hits["titles"] = _unique(list(hits.get("titles", [])) + ["software developer"])[:8]


def _score_family(
    family: RoleFamily,
    title_l: str,
    desc_l: str,
    full_l: str,
) -> Tuple[float, Dict[str, List[str]]]:
    score = 0.0
    title_hits: List[str] = []
    skill_hits: List[str] = []
    resp_hits: List[str] = []

    for term in all_title_terms(family):
        term_l = term.casefold().strip()
        if len(term_l) < 3:
            continue
        if term_l in title_l:
            score += 12
            title_hits.append(term)
        elif term_l in desc_l:
            score += 4
            title_hits.append(term)

    for skill in family.skills:
        skill_l = skill.casefold()
        if len(skill_l) < 2:
            continue
        if _term_in_text(skill_l, full_l):
            score += 2.5
            skill_hits.append(skill)

    for resp in family.responsibilities:
        resp_l = resp.casefold()
        if len(resp_l) < 4:
            continue
        if resp_l in full_l:
            score += 3
            resp_hits.append(resp)

    for degree in family.degrees:
        if degree.casefold() in full_l:
            score += 1.5

    # Cap runaway description spam
    score = min(score, 48)
    return score, {
        "titles": _unique(title_hits)[:8],
        "skills": _unique(skill_hits)[:10],
        "responsibilities": _unique(resp_hits)[:10],
    }


def _discovery_from_score(score: float, family: Optional[RoleFamily]) -> str:
    if score >= 14:
        return "high"
    if score >= 8:
        return family.default_discovery if family else "medium"
    if score >= 5:
        return "medium"
    return "low"


def _primary_seniority(levels: Sequence[str], title_l: str) -> Optional[str]:
    if not levels:
        return None
    # If junior is offered alongside senior, seniority is mixed / junior-accessible.
    if "junior" in levels or "intern" in levels:
        return "junior_accessible" if "senior" in levels else "junior"
    if "specialist" in levels and "senior" in levels:
        return "mixed"
    if "senior" in levels:
        return "senior"
    if "mid" in levels:
        return "mid"
    if "specialist" in levels:
        return "specialist"
    return levels[0]


def _build_reasons(
    primary_id: str,
    filter_group: str,
    discovery: str,
    hits: Dict[str, List[str]],
    levels: Sequence[str],
    education: str,
) -> List[str]:
    reasons = [f"primary:{primary_id}", f"group:{filter_group}", f"discovery:{discovery}"]
    if hits.get("titles"):
        reasons.append("title:" + ", ".join(hits["titles"][:3]))
    if hits.get("skills"):
        reasons.append("skills:" + ", ".join(hits["skills"][:4]))
    if levels:
        reasons.append("levels:" + "/".join(levels))
    if education != "unknown":
        reasons.append(f"education:{education}")
    return reasons


def _resolve_family(family_id: str) -> Optional[RoleFamily]:
    for family in ROLE_FAMILIES:
        if family.id == family_id:
            return family
    return None


def _looks_analytical_title(title_l: str) -> bool:
    markers = (
        "analyst",
        "analist",
        "controlling",
        "fp&a",
        "planning",
        "performance",
        "reporting",
        "commercial",
        "revenue",
        "budget",
        "cost analyst",
    )
    return any(marker in title_l for marker in markers)


def _has_software_qa_signals(text_l: str) -> bool:
    return _contains_any(
        text_l,
        (
            "software test",
            "test automation",
            "selenium",
            "cypress",
            "pytest",
            "qa engineer",
            "softwaretester",
            "testfälle",
            "test cases",
            "bug tracking",
            "regression test",
        ),
    )


def _strip_negated_tech_phrases(text_l: str) -> str:
    """Remove 'no/kein software…' style phrases so negation is not a positive hit."""
    patterns = (
        r"\bno\s+(?:software|it|data|sql|programming|coding)(?:\s+\w+){0,3}",
        r"\bkein(?:e|en)?\s+(?:software|it|daten|programmierung)(?:\s+\w+){0,3}",
        r"\bwithout\s+(?:software|it|programming)(?:\s+\w+){0,3}",
        r"\bnot\s+(?:a\s+)?(?:software|it)\s+(?:role|job|position)",
    )
    cleaned = text_l
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned)
    return cleaned


def _is_clearly_non_it_engineering(title_l: str, full_l: str) -> bool:
    markers = (
        "mechanical design",
        "mechanical engineer",
        "civil engineer",
        "structural engineer",
        "chemical engineer",
        "bauingenieur",
        "maschinenbau",
        "konstruktion",
        "solidworks",
        "catia",
        "inşaat",
        "makine mühendisi",
    )
    if not _contains_any(title_l, markers) and not _contains_any(full_l, markers):
        return False
    # Allow keep only when title itself is clearly software/IT.
    return not bool(
        re.search(r"\b(software|informatik|it\b|data|devops|cyber|sap)\b", title_l)
    )


def _contains_any(text_l: str, terms: Sequence[str]) -> bool:
    return any(term.casefold() in text_l for term in terms)


def _find_terms(text_l: str, terms: Sequence[str]) -> List[str]:
    found = []
    for term in terms:
        if term.casefold() in text_l:
            found.append(term)
    return found


def _term_in_text(term_l: str, text_l: str) -> bool:
    # Always use token boundaries for short/ambiguous tech tokens.
    if len(term_l) <= 4 or term_l in {"rest", "java", "node", "ruby", "rust", "perl", "bash"}:
        return bool(
            re.search(
                rf"(?<![a-z0-9_+#.]){re.escape(term_l)}(?![a-z0-9_+#.])",
                text_l,
            )
        )
    return term_l in text_l


def _unique(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
