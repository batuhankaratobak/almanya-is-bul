"""Search terms derived from the role taxonomy (+ limited MVP refresh seeds)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from app.config.role_taxonomy import (
    FILTER_GROUP_ALIASES,
    generate_search_terms,
    list_filter_groups,
)

CONFIG_PATH = Path(__file__).with_name("search_terms.json")

VALID_LANGUAGES = ("de", "en", "tr")


class UnknownCategoryError(ValueError):
    """Raised when a requested category is not defined."""


@lru_cache(maxsize=1)
def _load_config() -> Dict[str, object]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if "entry_level" not in data:
        raise ValueError("search_terms.json must contain entry_level")
    return data


def list_categories() -> List[str]:
    """Return filter-group ids used for search/category filtering."""
    # Prefer taxonomy order; keep legacy aliases for API/profile compatibility.
    primary = [g.id for g in list_filter_groups(include_legacy=False)]
    legacy = [g.id for g in list_filter_groups(include_legacy=True) if g.id in FILTER_GROUP_ALIASES]
    # Preserve previous MVP order for the original seven groups first.
    preferred = [
        "software_development",
        "it_support",
        "cybersecurity",
        "qa_testing",
        "system_administration",
        "application_support",
        "it_consulting",
    ]
    ordered: List[str] = []
    for item in preferred:
        if item in primary or item in legacy:
            ordered.append(item)
    for item in primary:
        if item not in ordered:
            ordered.append(item)
    for item in legacy:
        if item not in ordered:
            ordered.append(item)
    return ordered


def get_entry_level_keywords(language: Optional[str] = None) -> List[str]:
    """Return entry-level modifiers, optionally filtered by language."""
    entry_level = _load_config()["entry_level"]
    return _unique_preserve_order(_terms_for_languages(entry_level, language))


def get_mvp_refresh_queries() -> List[str]:
    """
    Limited representative query set for refresh runs.

    Uses search_terms.json when configured; otherwise a short taxonomy seed.
    """
    configured = _load_config().get("mvp_refresh_queries") or []
    if isinstance(configured, list) and configured:
        return _unique_preserve_order([str(item) for item in configured])

    terms: List[str] = []
    for category in list_categories()[:12]:
        generated = generate_search_terms(filter_group=category, market="de")
        terms.extend(generated[:2])
    return _unique_preserve_order(terms)


def get_search_terms(
    category: Optional[str] = None,
    language: Optional[str] = None,
    market: str = "de",
) -> List[str]:
    """
    Return unique search terms derived from the role taxonomy.

    - category=None → all filter groups
    - language=None → market default languages (DE+EN for Germany)
    - language='de' | 'en' | 'tr' → only that language
    """
    _validate_language(language)
    categories = list_categories()

    if category is not None:
        if category not in categories and category not in FILTER_GROUP_ALIASES:
            available = ", ".join(categories)
            raise UnknownCategoryError(
                f"Unknown category '{category}'. Available: {available}"
            )
        return generate_search_terms(
            filter_group=category,
            language=language,
            market=market,
        )

    terms: List[str] = []
    for group_id in categories:
        # Skip pure legacy aliases when collecting "all" to reduce duplicates;
        # generate_search_terms already dedupes, but aliases overlap heavily.
        if group_id in FILTER_GROUP_ALIASES:
            continue
        terms.extend(
            generate_search_terms(
                filter_group=group_id,
                language=language,
                market=market,
            )
        )
    return _unique_preserve_order(terms)


def _validate_language(language: Optional[str]) -> None:
    if language is None:
        return
    if language not in VALID_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. Use one of: {', '.join(VALID_LANGUAGES)}"
        )


def _terms_for_languages(
    language_map: Dict[str, Sequence[str]],
    language: Optional[str],
) -> List[str]:
    if language is not None:
        return list(language_map.get(language, []))

    terms: List[str] = []
    for lang in ("de", "en", "tr"):
        terms.extend(language_map.get(lang, []))
    return terms


def _unique_preserve_order(terms: Sequence[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique
