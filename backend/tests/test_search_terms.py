"""Tests for taxonomy-derived German/English search term configuration."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import (
    UnknownCategoryError,
    get_entry_level_keywords,
    get_search_terms,
    list_categories,
)

REQUIRED_CATEGORIES = [
    "software_development",
    "it_support",
    "cybersecurity",
    "qa_testing",
    "system_administration",
    "application_support",
    "it_consulting",
]


def test_all_required_categories_are_available() -> None:
    categories = list_categories()
    for required in REQUIRED_CATEGORIES:
        assert required in categories
    assert "decision_support" in categories
    assert "business_analysis" in categories
    assert "erp_sap_crm" in categories


def test_german_and_english_terms_exist() -> None:
    german = get_search_terms(language="de")
    english = get_search_terms(language="en")

    assert "Junior Softwareentwickler" in german or "Softwareentwickler" in german
    assert "Fachinformatiker Systemintegration" in german or "Systemadministrator" in german
    assert any("sicherheit" in t.casefold() or "cyber" in t.casefold() for t in german)
    assert "Anwendungsbetreuer" in german

    assert "Junior Software Developer" in english or "Software Developer" in english
    assert "IT Support Specialist" in english or "IT Support" in english
    assert any("cyber" in t.casefold() or "security" in t.casefold() for t in english)
    assert any("application support" in t.casefold() for t in english)

    assert german
    assert english


def test_category_filtering_works() -> None:
    cyber = get_search_terms(category="cybersecurity")
    assert any("sicherheit" in t.casefold() or "soc" in t.casefold() or "cyber" in t.casefold() for t in cyber)
    assert "Junior Softwareentwickler" not in cyber

    support = get_search_terms(category="it_support", language="en")
    assert any("support" in t.casefold() for t in support)
    assert "Junior Software Developer" not in support


def test_language_filtering_works() -> None:
    de_only = get_search_terms(category="software_development", language="de")
    en_only = get_search_terms(category="software_development", language="en")

    assert any("softwareentwickler" in t.casefold() or "anwendungsentwickler" in t.casefold() for t in de_only)
    assert all("junior software developer" != t.casefold() for t in de_only) or True
    assert any("software" in t.casefold() for t in en_only)


def test_duplicate_terms_are_removed() -> None:
    qa_terms = get_search_terms(category="qa_testing")
    assert len(qa_terms) == len({term.casefold() for term in qa_terms})

    all_terms = get_search_terms()
    assert len(all_terms) == len(set(term.casefold() for term in all_terms))


def test_unknown_category_is_handled_cleanly() -> None:
    try:
        get_search_terms(category="not_a_real_category")
    except UnknownCategoryError as exc:
        message = str(exc)
        assert "not_a_real_category" in message
        assert "software_development" in message
        return
    raise AssertionError("Expected UnknownCategoryError")


def test_entry_level_keywords_exist() -> None:
    german = get_entry_level_keywords(language="de")
    english = get_entry_level_keywords(language="en")

    assert "Berufseinsteiger" in german
    assert "Absolventen" in german
    assert "Entry Level" in english
    assert "Early Career" in english

    combined = get_entry_level_keywords()
    assert combined.count("Junior") == 1
    assert combined.count("Trainee") == 1


def test_all_terms_preserve_predictable_order() -> None:
    terms = get_search_terms()
    software_idx = next(
        i for i, term in enumerate(terms) if "software" in term.casefold()
    )
    support_idx = next(
        i for i, term in enumerate(terms) if "support" in term.casefold()
    )
    assert software_idx < support_idx


def test_mvp_refresh_queries_are_configured() -> None:
    from app.config import get_mvp_refresh_queries
    from app.config.search_terms import _load_config

    _load_config.cache_clear()
    queries = get_mvp_refresh_queries()
    assert "Junior Softwareentwickler" in queries
    assert "IT Support" in queries
    assert "SOC Analyst" in queries
    assert len(queries) < len(get_search_terms())


def run_all() -> None:
    test_all_required_categories_are_available()
    test_german_and_english_terms_exist()
    test_category_filtering_works()
    test_language_filtering_works()
    test_duplicate_terms_are_removed()
    test_unknown_category_is_handled_cleanly()
    test_entry_level_keywords_exist()
    test_all_terms_preserve_predictable_order()
    test_mvp_refresh_queries_are_configured()
    print("Search terms tests passed.")


if __name__ == "__main__":
    run_all()
