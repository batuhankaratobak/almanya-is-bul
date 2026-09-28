"""Translate English CV narrative fields to German (cached on the profile)."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _fingerprint(profile: Dict[str, Any]) -> str:
    payload = {
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "education": profile.get("education"),
        "experiences": profile.get("experiences"),
        "projects": profile.get("projects"),
    }
    raw = repr(payload).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


# Keep academic/professional titles accurate (MT often mangles these).
_FIXED_DE: Dict[str, str] = {
    "B.Sc. Computer Engineering": "B.Sc. Computer Engineering (Informatik)",
    "Bachelor's degree in Computer Engineering.": (
        "Bachelor of Science in Computer Engineering (Informatik)."
    ),
    "Bachelor's degree in Computer Engineering": (
        "Bachelor of Science in Computer Engineering (Informatik)"
    ),
    "Computer Engineer | IT Support & Systems | Junior Software": (
        "Computeringenieur | IT-Support & Systeme | Junior Software"
    ),
}


def _translate_text(text: str, *, translator) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if cleaned in _FIXED_DE:
        return _FIXED_DE[cleaned]
    # Keep short tech tokens as-is when translation would add little value.
    if len(cleaned) <= 2:
        return cleaned
    # Never machine-translate short degree titles containing Computer Engineering.
    if "computer engineering" in cleaned.casefold() and len(cleaned) < 120:
        if "bachelor" in cleaned.casefold() or "b.sc" in cleaned.casefold():
            if "degree" in cleaned.casefold() or cleaned.casefold().startswith("bachelor"):
                return "Bachelor of Science in Computer Engineering (Informatik)."
            return "B.Sc. Computer Engineering (Informatik)"
        if cleaned.casefold() in {"computer engineering"}:
            return "Computer Engineering (Informatik)"
        return cleaned.replace("Computer Engineering", "Computer Engineering (Informatik)")
    try:
        return translator.translate(cleaned)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CV translate failed: %s", exc)
        return cleaned


def ensure_german_translation(
    profile: Dict[str, Any],
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Fill profile['translations']['de'] from English source fields.

    Skips work when fingerprint matches and force is False.
    """
    data = dict(profile)
    translations = data.get("translations")
    if not isinstance(translations, dict):
        translations = {}
    existing_de = translations.get("de")
    if not isinstance(existing_de, dict):
        existing_de = {}

    fingerprint = _fingerprint(data)
    if (
        not force
        and existing_de.get("source_fingerprint") == fingerprint
        and existing_de.get("summary")
    ):
        data["translations"] = {**translations, "de": existing_de}
        data["translation_status"] = "cached"
        return data

    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source="en", target="de")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Translator unavailable: %s", exc)
        data["translations"] = {
            **translations,
            "de": existing_de or _copy_as_de(data, fingerprint, status="unavailable"),
        }
        data["translation_status"] = "unavailable"
        return data

    de: Dict[str, Any] = {
        "source_fingerprint": fingerprint,
        "headline": _translate_text(str(data.get("headline") or ""), translator=translator),
        "summary": _translate_text(str(data.get("summary") or ""), translator=translator),
        "education": _translate_education(data.get("education") or [], translator=translator),
        "experiences": _translate_experiences(
            data.get("experiences") or [], translator=translator
        ),
        "projects": _translate_projects(data.get("projects") or [], translator=translator),
    }
    # Keep the formal degree name visible in DE copy (MT often collapses it to "Informatik").
    summary_de = str(de.get("summary") or "")
    summary_de = summary_de.replace(
        "Absolvent der Informatik",
        "Absolvent der Computer Engineering / Informatik",
    )
    summary_de = summary_de.replace(
        "Absolventin der Informatik",
        "Absolventin der Computer Engineering / Informatik",
    )
    de["summary"] = summary_de
    data["translations"] = {**translations, "de": de}
    data["translation_status"] = "updated"
    return data


def resolve_localized_cv(profile: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Return a flat CV dict in the requested language (en|de)."""
    lang = "de" if lang == "de" else "en"
    base = dict(profile)
    if lang == "en":
        return base

    de = ((profile.get("translations") or {}).get("de")) or {}
    if not isinstance(de, dict) or not de.get("summary"):
        enriched = ensure_german_translation(profile, force=False)
        de = ((enriched.get("translations") or {}).get("de")) or {}
        base = enriched

    localized = dict(base)
    for key in ("headline", "summary", "education", "experiences", "projects"):
        if de.get(key):
            localized[key] = de[key]
    return localized


def _copy_as_de(
    profile: Dict[str, Any], fingerprint: str, *, status: str
) -> Dict[str, Any]:
    return {
        "source_fingerprint": fingerprint,
        "status": status,
        "headline": profile.get("headline") or "",
        "summary": profile.get("summary") or "",
        "education": profile.get("education") or [],
        "experiences": profile.get("experiences") or [],
        "projects": profile.get("projects") or [],
    }


def _translate_education(items: List[Any], *, translator) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        degree = str(item.get("degree") or "").strip()
        details = str(item.get("details") or "").strip()
        out.append(
            {
                **item,
                "school": str(item.get("school") or "").strip(),
                "degree": _translate_text(degree, translator=translator) if degree else "",
                "period": item.get("period") or "",
                "details": _translate_text(details, translator=translator) if details else "",
            }
        )
    return out


_MONTHS_DE = {
    "january": "Januar",
    "february": "Februar",
    "march": "März",
    "april": "April",
    "may": "Mai",
    "june": "Juni",
    "july": "Juli",
    "august": "August",
    "september": "September",
    "october": "Oktober",
    "november": "November",
    "december": "Dezember",
}


def _period_to_de(period: str) -> str:
    text = str(period or "")
    for en, de in _MONTHS_DE.items():
        text = re.sub(en, de, text, flags=re.IGNORECASE)
    text = re.sub(r"\bPresent\b", "heute", text, flags=re.IGNORECASE)
    return text


def _translate_experiences(items: List[Any], *, translator) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        bullets = item.get("bullets") if isinstance(item.get("bullets"), list) else []
        org = str(item.get("org") or "")
        org_de = org
        org_de = re.sub(r"\bMunicipality\b", "Stadtverwaltung", org_de, flags=re.IGNORECASE)
        org_de = re.sub(r"\bIT Department\b", "IT-Abteilung", org_de, flags=re.IGNORECASE)
        title = str(item.get("title") or "")
        title_de = _translate_text(title, translator=translator)
        if title.casefold() in {"it intern", "it internship"}:
            title_de = "IT-Praktikant"
        out.append(
            {
                **item,
                "title": title_de,
                "org": org_de,
                "period": _period_to_de(str(item.get("period") or "")),
                "bullets": [
                    _translate_text(str(b), translator=translator) for b in bullets if str(b).strip()
                ],
            }
        )
    return out


_CURATED_PROJECTS_DE: Dict[str, Dict[str, Any]] = {
    "airport operations": {
        "name": "Airport Operations Control Center",
        "stack": ["Next.js", "React", "TypeScript", "Tailwind CSS", "Zustand"],
        "bullets": [
            "Produktives Next.js-Kontrollzentrum für Flughafenoperationen: Dashboard, Flüge, Gates und Alarme.",
            "SSR/SSG, React Server Components, typed REST-Routen und schlankes Client-State mit Zustand umgesetzt.",
            "Responsive Desktop-/Mobil-UI, CI (Lint/Typecheck/Smoke-Tests) und Deployment auf Vercel.",
        ],
    },
}


def _translate_projects(items: List[Any], *, translator) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        curated = None
        low = name.casefold()
        for key, block in _CURATED_PROJECTS_DE.items():
            if key in low:
                curated = block
                break
        if curated:
            out.append({**item, **curated})
            continue
        bullets = item.get("bullets") if isinstance(item.get("bullets"), list) else []
        out.append(
            {
                **item,
                "name": item.get("name") or "",
                "stack": item.get("stack") if isinstance(item.get("stack"), list) else [],
                "bullets": [
                    _translate_text(str(b), translator=translator) for b in bullets if str(b).strip()
                ],
            }
        )
    return out


def detect_output_language(
    *,
    job_language: Optional[str],
    title: str = "",
    description: str = "",
    override: Optional[str] = None,
) -> str:
    if override in {"en", "de"}:
        return override
    lang = (job_language or "").casefold()
    if lang.startswith("de") and "en" not in lang:
        return "de"
    if lang in {"de/en", "en/de", "mixed"}:
        # Prefer German for DE market mixed ads when German signals dominate.
        blob = f"{title}\n{description}".casefold()
        de_hits = sum(1 for w in (" und ", " mit ", "kenntnisse", "erfahrung", "bewerbung") if w in blob)
        en_hits = sum(1 for w in (" and ", " with ", "experience", "requirements", "looking for") if w in blob)
        return "de" if de_hits >= en_hits else "en"
    if lang.startswith("en"):
        return "en"
    blob = f"{title}\n{description}".casefold()
    if any(w in blob for w in ("kenntnisse", "anforderungen", "bewerbung", "unternehmen")):
        return "de"
    return "en"
