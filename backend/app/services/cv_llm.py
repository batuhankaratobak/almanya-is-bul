"""Rewrite selected CV slices and Anschreiben via local Ollama (optional)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from app.services.cv_tailor import TailoredSelection
from app.services.ollama_client import chat_json

logger = logging.getLogger(__name__)


def rewrite_tailored_cv(
    tailored: TailoredSelection,
    *,
    title: str,
    company: str,
    description: str,
    lang: str,
) -> TailoredSelection:
    """Rewrite summary/bullets to the job. Keep facts; fall back on failure."""
    payload = chat_json(
        system=_cv_system(lang),
        user=_cv_user(
            tailored,
            title=title,
            company=company,
            description=description,
            lang=lang,
        ),
    )
    if not payload:
        return tailored
    return _merge_cv(tailored, payload)


def rewrite_cover_paragraphs(
    *,
    title: str,
    company: str,
    description: str,
    lang: str,
    skills: Sequence[str],
    experiences: Sequence[Dict[str, Any]],
    projects: Sequence[Dict[str, Any]],
    fallback: List[str],
) -> List[str]:
    payload = chat_json(
        system=_letter_system(lang),
        user=_letter_user(
            title=title,
            company=company,
            description=description,
            lang=lang,
            skills=skills,
            experiences=experiences,
            projects=projects,
        ),
    )
    if not payload:
        return fallback
    paragraphs = payload.get("paragraphs")
    if not isinstance(paragraphs, list):
        return fallback
    cleaned = [str(p).strip() for p in paragraphs if str(p).strip()]
    if lang == "de":
        if not cleaned or not cleaned[0].lower().startswith("sehr geehrte"):
            cleaned = ["Sehr geehrte Damen und Herren,"] + cleaned
    else:
        if not cleaned or not cleaned[0].lower().startswith("dear"):
            cleaned = ["Dear Hiring Team,"] + cleaned
    return cleaned[:5] or fallback


def _cv_system(lang: str) -> str:
    language = "German" if lang == "de" else "English"
    return (
        "You rewrite a junior candidate CV for ONE job. Output JSON only. "
        f"Write all prose in {language}. "
        "Rules: do not invent employers, dates, degrees, tools, or achievements. "
        "You may rephrase existing bullets to emphasize overlap with the job. "
        "Do not claim professional eye-tracking hardware, real airport systems, "
        "or production SaaS if the source says portfolio/mock/internship. "
        "Keep degree names, employer names, dates and project scope faithful to the input. "
        "JSON keys: headline, summary, fit_points (array of 3 strings), "
        "experiences (array of {title, bullets}), projects (array of {name, bullets})."
    )


def _cv_user(
    tailored: TailoredSelection,
    *,
    title: str,
    company: str,
    description: str,
    lang: str,
) -> str:
    desc = (description or "")[:1800]
    return (
        f"JOB TITLE: {title}\nCOMPANY: {company}\nLANGUAGE: {lang}\n"
        f"JOB DESCRIPTION:\n{desc}\n\n"
        f"SELECTED HEADLINE: {tailored.headline}\n"
        f"SELECTED SUMMARY: {tailored.summary}\n"
        f"SELECTED SKILLS: {', '.join(tailored.skills[:12])}\n"
        f"EXPERIENCES: {tailored.experiences}\n"
        f"PROJECTS: {tailored.projects}\n"
        "Rewrite headline/summary/fit_points and the bullets of the given experiences/projects only. "
        "Keep title/org/period/name/stack unchanged in meaning."
    )


def _letter_system(lang: str) -> str:
    language = "German" if lang == "de" else "English"
    greet = (
        "Start with 'Sehr geehrte Damen und Herren,'"
        if lang == "de"
        else "Start with 'Dear Hiring Team,'"
    )
    return (
        "You write a short German-style Anschreiben / cover letter. JSON only. "
        f"Language: {language}. {greet} then 3 body paragraphs. "
        "No fake experience. Mention 1-2 real projects or internships from the input. "
        "Do not mention that a tool or AI generated this. "
        'JSON: {"paragraphs": ["...", "...", "...", "..."]}'
    )


def _letter_user(
    *,
    title: str,
    company: str,
    description: str,
    lang: str,
    skills: Sequence[str],
    experiences: Sequence[Dict[str, Any]],
    projects: Sequence[Dict[str, Any]],
) -> str:
    desc = (description or "")[:1200]
    return (
        f"JOB: {title}\nCOMPANY: {company}\nLANGUAGE: {lang}\n"
        f"DESCRIPTION:\n{desc}\n"
        f"SKILLS: {', '.join(list(skills)[:8])}\n"
        f"EXPERIENCE: {list(experiences)[:3]}\n"
        f"PROJECTS: {list(projects)[:3]}\n"
    )


def _merge_cv(base: TailoredSelection, payload: Dict[str, Any]) -> TailoredSelection:
    headline = str(payload.get("headline") or base.headline).strip() or base.headline
    summary = str(payload.get("summary") or base.summary).strip() or base.summary
    fit = payload.get("fit_points")
    if isinstance(fit, list):
        fit_points = [str(x).strip() for x in fit if str(x).strip()][:3]
    else:
        fit_points = base.requirement_lines

    experiences = _merge_blocks(
        base.experiences,
        payload.get("experiences"),
        name_key="title",
        bullet_limit=4,
    )
    projects = _merge_blocks(
        base.projects,
        payload.get("projects"),
        name_key="name",
        bullet_limit=3,
    )
    return TailoredSelection(
        focus=base.focus,
        headline=headline[:120],
        summary=summary[:900],
        skills=base.skills,
        other_skills=base.other_skills,
        experiences=experiences,
        projects=projects,
        requirement_lines=fit_points or base.requirement_lines,
    )


def _merge_blocks(
    originals: List[Dict[str, Any]],
    incoming: Any,
    *,
    name_key: str,
    bullet_limit: int,
) -> List[Dict[str, Any]]:
    if not isinstance(incoming, list) or not originals:
        return originals
    by_name = {}
    for item in incoming:
        if not isinstance(item, dict):
            continue
        key = str(item.get(name_key) or "").strip().casefold()
        bullets = item.get("bullets")
        if key and isinstance(bullets, list):
            by_name[key] = [str(b).strip() for b in bullets if str(b).strip()][:bullet_limit]
    out: List[Dict[str, Any]] = []
    for block in originals:
        key = str(block.get(name_key) or "").strip().casefold()
        merged = dict(block)
        if key in by_name and by_name[key]:
            merged["bullets"] = by_name[key]
        out.append(merged)
    return out
