"""Extract recognizable technical skills from job text."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Set, Tuple

# Canonical skill → match patterns (case-insensitive).
SKILL_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Python", (r"\bpython\b",)),
    ("Java", (r"\bjava\b(?!script)",)),
    ("C", (r"(?<![a-z])\bc(?!\+\+|#|\.)\b", r"\bc language\b")),
    ("C++", (r"\bc\+\+\b", r"\bcpp\b")),
    ("C#", (r"\bc#\b", r"\bcsharp\b")),
    (".NET", (r"\b\.?net\b", r"\bdotnet\b")),
    ("JavaScript", (r"\bjavascript\b", r"\bjs\b")),
    ("TypeScript", (r"\btypescript\b", r"\bts\b")),
    ("React", (r"\breact(?:\.?js)?\b",)),
    ("Angular", (r"\bangular\b",)),
    ("Vue", (r"\bvue(?:\.?js)?\b",)),
    ("Node.js", (r"\bnode\.?js\b", r"\bnodejs\b")),
    ("SQL", (r"\bsql\b",)),
    ("PostgreSQL", (r"\bpostgresql\b", r"\bpostgres\b")),
    ("MySQL", (r"\bmysql\b",)),
    ("SQLite", (r"\bsqlite\b",)),
    ("Docker", (r"\bdocker\b",)),
    ("Kubernetes", (r"\bkubernetes\b", r"\bk8s\b")),
    ("AWS", (r"\baws\b", r"\bamazon web services\b")),
    ("Azure", (r"\bazure\b",)),
    ("Linux", (r"\blinux\b",)),
    ("Windows", (r"\bwindows\b",)),
    ("Office 365", (r"\boffice\s*365\b", r"\bmicrosoft\s*365\b", r"\bm365\b")),
    ("Microsoft 365", (r"\bmicrosoft\s*365\b", r"\bm365\b")),
    ("Active Directory", (r"\bactive\s*directory\b", r"\bad\b")),
    ("TCP/IP", (r"\btcp/?ip\b",)),
    ("Git", (r"\bgit\b",)),
    ("GitHub", (r"\bgithub\b",)),
    ("REST", (r"\brest(?:ful)?\b", r"\brest\s*api\b")),
    ("FastAPI", (r"\bfastapi\b",)),
    ("Spring", (r"\bspring\b", r"\bspring\s*boot\b")),
    ("SAP", (r"\bsap\b",)),
    ("PowerShell", (r"\bpowershell\b",)),
    ("Cybersecurity", (r"\bcyber\s*security\b", r"\bcybersecurity\b", r"\binformationssicherheit\b")),
    ("SIEM", (r"\bsiem\b",)),
    ("SOC", (r"\bsoc\b", r"\bsecurity operations\b")),
    ("Jira", (r"\bjira\b",)),
    ("HTML", (r"\bhtml5?\b",)),
    ("CSS", (r"\bcss3?\b",)),
)


def extract_skills(text: str) -> List[str]:
    """Return canonical skills found in text (stable order)."""
    if not text or not text.strip():
        return []
    hay = text
    found: List[str] = []
    seen: Set[str] = set()
    for skill, patterns in SKILL_PATTERNS:
        if skill in seen:
            continue
        for pattern in patterns:
            if re.search(pattern, hay, flags=re.IGNORECASE):
                found.append(skill)
                seen.add(skill)
                break
    return found


def compare_skills(
    job_skills: Sequence[str],
    profile_skills: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """
    Return (matched_skills, missing_skills).

    missing = skills found in the job that are not in the candidate profile.
    """
    profile_keys = {_norm(skill) for skill in profile_skills if skill and skill.strip()}
    matched: List[str] = []
    missing: List[str] = []
    for skill in job_skills:
        if _norm(skill) in profile_keys:
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing


def normalize_skill_list(skills: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for skill in skills:
        cleaned = (skill or "").strip()
        if not cleaned:
            continue
        key = _norm(cleaned)
        if key in seen:
            continue
        seen.add(key)
        # Prefer canonical casing when known.
        canonical = next((name for name, _ in SKILL_PATTERNS if _norm(name) == key), cleaned)
        result.append(canonical)
    return result


def _norm(value: str) -> str:
    return value.casefold().strip()
