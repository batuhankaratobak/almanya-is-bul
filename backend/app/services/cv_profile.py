"""Local CV narrative profile used to generate tailored A4 Word applications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.db import session as db_session
from app.services.candidate_profile import load_profile
from app.services.cv_translate import ensure_german_translation


def _cv_path() -> Path:
    return Path(db_session.DATABASE_PATH).parent / "cv_profile.json"


def get_default_cv_profile() -> Dict[str, Any]:
    scoring = load_profile()
    return {
        "source_language": "en",
        "full_name": "",
        "email": "",
        "phone": "",
        "city": "Germany",
        "linkedin_or_github": "",
        "headline": "Junior Software Developer | Computer Engineering Graduate",
        "summary": (
            "Computer Engineering graduate seeking junior software / IT support roles in Germany. "
            "I build with Python, JavaScript/TypeScript, React, SQL and Git. "
            "I am targeting entry-level and Berufseinsteiger positions."
        ),
        "education": [
            {
                "school": scoring.get("education") or "Computer Engineering / Informatik",
                "degree": "Bachelor's degree",
                "period": "",
                "details": "",
            }
        ],
        "experiences": [
            {
                "title": "Software / Project Experience",
                "org": "Personal & Academic Projects",
                "period": "2023 – 2026",
                "bullets": [
                    "Built backend APIs with Python and FastAPI.",
                    "Created web interfaces with React and TypeScript.",
                    "Designed SQL/SQLite data models and queries.",
                    "Used Git/GitHub for version control and project workflow.",
                ],
            }
        ],
        "projects": [
            {
                "name": "Germany Job Hunter",
                "stack": ["Python", "FastAPI", "React", "SQLite"],
                "bullets": [
                    "Built a local app that collects job listings from multiple sources.",
                    "Implemented normalization, deduplication and profile-based scoring.",
                ],
            }
        ],
        "skills": list(scoring.get("skills") or []),
        "languages": [
            {"name": "German", "level": scoring.get("german_level") or "B1"},
            {"name": "English", "level": scoring.get("english_level") or "B2"},
        ],
        "translations": {},
        "translation_status": "pending",
    }


def normalize_cv_profile(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    base = get_default_cv_profile()
    data = {**base, **(payload or {})}

    def clean_list(items: Any) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        out: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                out.append(item)
        return out

    data["source_language"] = "en"
    data["full_name"] = str(data.get("full_name") or "").strip()
    data["email"] = str(data.get("email") or "").strip()
    data["phone"] = str(data.get("phone") or "").strip()
    data["city"] = str(data.get("city") or "").strip()
    data["linkedin_or_github"] = str(data.get("linkedin_or_github") or "").strip()
    data["headline"] = str(data.get("headline") or "").strip()
    data["summary"] = str(data.get("summary") or "").strip()
    data["education"] = clean_list(data.get("education"))
    data["experiences"] = clean_list(data.get("experiences"))
    data["projects"] = clean_list(data.get("projects"))
    skills = data.get("skills")
    if isinstance(skills, list):
        data["skills"] = [str(s).strip() for s in skills if str(s).strip()]
    else:
        data["skills"] = []
    data["languages"] = clean_list(data.get("languages"))
    translations = data.get("translations")
    data["translations"] = translations if isinstance(translations, dict) else {}
    return data


def load_cv_profile() -> Dict[str, Any]:
    path = _cv_path()
    if not path.exists():
        profile = get_default_cv_profile()
        return save_cv_profile(profile, translate=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return get_default_cv_profile()
    if not isinstance(payload, dict):
        return get_default_cv_profile()
    normalized = normalize_cv_profile(payload)
    de = (normalized.get("translations") or {}).get("de")
    if not isinstance(de, dict) or not de.get("summary"):
        return save_cv_profile(normalized, translate=True)
    return normalized


def save_cv_profile(profile: Dict[str, Any], *, translate: bool = True) -> Dict[str, Any]:
    normalized = normalize_cv_profile(profile)
    if translate:
        normalized = ensure_german_translation(normalized, force=True)
    path = _cv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def refresh_german_translation() -> Dict[str, Any]:
    current = load_cv_profile()
    return save_cv_profile(current, translate=True)
