"""Shared Germany / role-discovery filters for feed-style sources."""

from __future__ import annotations

import re
from typing import Any, Dict, Sequence

from app.services.role_classifier import classify_job, is_discovery_keep


_GERMANY_POSITIVE = (
    "germany",
    "deutschland",
    "berlin",
    "munich",
    "münchen",
    "muenchen",
    "hamburg",
    "köln",
    "koeln",
    "cologne",
    "frankfurt",
    "stuttgart",
    "düsseldorf",
    "duesseldorf",
    "leipzig",
    "dresden",
    "hannover",
    "nürnberg",
    "nuernberg",
    "nuremberg",
    "bremen",
    "essen",
    "dortmund",
    "bonn",
    "mannheim",
    "karlsruhe",
    "freiburg",
    "heidelberg",
    "aachen",
    "wiesbaden",
    "mainz",
    "kiel",
    "rostock",
    "potsdam",
    "erfurt",
    "saarbrücken",
    "bielefeld",
    "bochum",
    "wuppertal",
    "hessen",
    "bayern",
    "bavaria",
    "baden",
    "nordrhein",
    "nrw",
    "niedersachsen",
    "sachsen",
    "saxony",
    "de remote",
    "remote de",
    "remote germany",
    "deutschlandweit",
)

_NON_GERMANY_STRONG = (
    "netherlands only",
    "france only",
    "spain only",
    "uk only",
    "united states",
    "usa only",
    "switzerland only",
    "austria only",
    "switzerland",
    "schweiz",
    "swissit",
    "zürich, switzerland",
    "zurich, switzerland",
    "wien, österreich",
    "vienna, austria",
)


def text_blob(item: Dict[str, Any], *keys: str) -> str:
    parts = []
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        else:
            parts.append(str(value))
    return " ".join(parts)


def is_germany_relevant(item: Dict[str, Any]) -> bool:
    haystack = text_blob(
        item, "location", "title", "slug", "description", "country", "company_name", "company"
    ).casefold()
    has_germany = any(marker in haystack for marker in _GERMANY_POSITIVE)
    if re.search(r"(?:^|[\s,/(-])de(?:$|[\s,/)-])", haystack):
        has_germany = True
    if item.get("country") and str(item.get("country")).casefold() in {
        "de",
        "deu",
        "deutschland",
        "germany",
    }:
        has_germany = True
    # Common German gender-neutral title marker on DE boards (often with empty location).
    title = str(item.get("title") or "")
    location = str(item.get("location") or "").strip()
    if re.search(r"\((?:m\s*/\s*w\s*/\s*d|w\s*/\s*m\s*/\s*d|m\s*/\s*f\s*/\s*d)\)", title, re.I):
        if not location or location.casefold() in {"remote", "deutschland", "germany", "de"}:
            has_germany = True
    has_non_germany = any(marker in haystack for marker in _NON_GERMANY_STRONG)
    if has_germany and not has_non_germany:
        return True
    if has_germany and has_non_germany:
        # Keep only when Germany is explicitly present alongside other countries.
        return ("germany" in haystack or "deutschland" in haystack) and not any(
            marker in haystack for marker in ("switzerland", "schweiz", "swissit")
        )
    return False


def matches_target_role(
    item: Dict[str, Any],
    search_terms: Sequence[str],
    target_categories: Sequence[str],
) -> bool:
    """
    Keep HIGH/MEDIUM discovery jobs for Computer Engineering career paths.

    Do not discard solely because the title lacks a narrow IT keyword.
    Candidate match scoring happens later and may still rank the job low.
    """
    title = str(item.get("title") or "")
    description = str(item.get("description") or "")
    tags = item.get("tags") if isinstance(item.get("tags"), list) else []
    extra = " ".join(str(t) for t in tags)
    classification = classify_job(title, description, extra_text=extra)

    if is_discovery_keep(classification):
        return True

    # Fallback: explicit search-term hit in title/description (controlled discovery).
    hay = f"{title}\n{description}\n{extra}".casefold()
    for term in search_terms:
        cleaned = term.strip()
        if len(cleaned) < 4:
            continue
        if cleaned.casefold() in hay:
            return True

    # Low-discovery jobs are discarded unless a concrete search-term hit above.
    return False
