"""Single local editable candidate profile (no auth, no multi-user)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.db import session as db_session

DEFAULT_PROFILE: Dict[str, Any] = {
    "target_roles": [
        "Junior Software Developer",
        "Junior Softwareentwickler",
        "IT Support",
        "Junior Cyber Security Analyst",
        "Junior QA Engineer",
        "Junior System Administrator",
        "Application Support",
        "Junior IT Consultant",
    ],
    "target_categories": [
        "software_development",
        "it_support",
        "system_infrastructure",
        "network",
        "cybersecurity",
        "data_database",
        "bi_reporting",
        "decision_support",
        "business_analysis",
        "erp_sap_crm",
        "cloud_devops",
        "qa_testing",
        "digital_transformation",
        "project_pmo",
        "product",
        "operations",
        "industrial_it",
        "consulting_implementation",
        "planning_performance",
        "financial_analytics",
        "supply_chain_analytics",
        "ai_ml",
        "system_administration",
        "application_support",
        "it_consulting",
    ],
    "skills": [
        "Python",
        "Java",
        "C",
        "C++",
        "JavaScript",
        "TypeScript",
        "React",
        "SQL",
        "PostgreSQL",
        "SQLite",
        "Git",
        "GitHub",
        "Docker",
        "FastAPI",
        "Node.js",
        "HTML",
        "CSS",
        "TCP/IP",
        "Windows",
        "Linux",
    ],
    "experience_areas": [
        "Software Development",
        "Web Development",
        "IT Support",
        "Databases",
        "Networking basics",
    ],
    "education": "Computer Engineering / Informatik",
    "german_level": "B1",
    "english_level": "B2",
    "preferred_max_experience_years": 2,
    "preferred_work_models": ["hybrid", "remote", "onsite"],
    "preferred_locations": ["Germany", "Berlin", "München", "Hamburg", "Remote"],
    "unwanted_roles": [
        "Senior",
        "Lead",
        "Principal",
        "Staff Engineer",
        "Engineering Manager",
    ],
}


def _profile_path() -> Path:
    return Path(db_session.DATABASE_PATH).parent / "candidate_profile.json"


def get_default_profile() -> Dict[str, Any]:
    return deepcopy(DEFAULT_PROFILE)


def load_profile() -> Dict[str, Any]:
    path = _profile_path()
    if not path.exists():
        profile = get_default_profile()
        save_profile(profile)
        return profile
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return get_default_profile()
    if not isinstance(payload, dict):
        return get_default_profile()
    return normalize_profile(payload)


def save_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_profile(profile)
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    base = get_default_profile()
    data = {**base, **(profile or {})}

    def as_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [part.strip() for part in value.replace("\n", ",").split(",")]
            return [part for part in parts if part]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    data["target_roles"] = as_list(data.get("target_roles"))
    data["target_categories"] = as_list(data.get("target_categories"))
    data["skills"] = as_list(data.get("skills"))
    data["experience_areas"] = as_list(data.get("experience_areas"))
    data["preferred_work_models"] = [
        model for model in as_list(data.get("preferred_work_models")) if model in {"remote", "hybrid", "onsite"}
    ] or list(base["preferred_work_models"])
    data["preferred_locations"] = as_list(data.get("preferred_locations"))
    data["unwanted_roles"] = as_list(data.get("unwanted_roles"))
    data["education"] = str(data.get("education") or "").strip()
    data["german_level"] = str(data.get("german_level") or "unknown").strip().upper()
    data["english_level"] = str(data.get("english_level") or "unknown").strip().upper()
    try:
        years = int(data.get("preferred_max_experience_years") or 2)
    except (TypeError, ValueError):
        years = 2
    data["preferred_max_experience_years"] = max(0, min(years, 15))
    return data
