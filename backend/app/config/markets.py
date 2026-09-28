"""Target markets and compact cross-country search families."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

# Core production markets for this personal job hunter.
MARKETS: Tuple[str, ...] = ("DE", "CH", "FR", "NL")

MARKET_LABELS = {
    "DE": "Almanya",
    "CH": "İsviçre",
    "FR": "Fransa",
    "NL": "Hollanda",
}

# Adzuna country path segments.
ADZUNA_COUNTRY_CODES = {
    "DE": "de",
    "CH": "ch",
    "FR": "fr",
    "NL": "nl",
}

# Careerjet locale_code values (language_COUNTRY).
CAREERJET_LOCALES = {
    "DE": ("de_DE", "en_GB"),
    "CH": ("de_CH", "fr_CH", "en_GB"),
    "FR": ("fr_FR", "en_GB"),
    "NL": ("nl_NL", "en_GB"),
}

# Jooble / generic location strings.
MARKET_LOCATIONS = {
    "DE": "Germany",
    "CH": "Switzerland",
    "FR": "France",
    "NL": "Netherlands",
}

# Compact keyword families — do NOT explode into hundreds of requests.
KEYWORD_FAMILIES: Tuple[str, ...] = (
    "Software Developer",
    "Software Engineer",
    "IT Support",
    "System Administrator",
    "Cyber Security",
    "Data Analyst",
    "Business Analyst",
    "QA Tester",
    "DevOps Engineer",
    "SAP",
)


def get_keyword_families() -> List[str]:
    return list(KEYWORD_FAMILIES)


def get_markets() -> List[str]:
    return list(MARKETS)


def compact_queries_for_market(market: str, *, max_terms: int = 8) -> List[str]:
    """Return a short query set for one market refresh."""
    return list(KEYWORD_FAMILIES[:max_terms])


def cross_country_refresh_plan(
    markets: Sequence[str] | None = None,
    *,
    max_terms: int = 6,
    pages_per_query: int = 1,
) -> List[Dict[str, object]]:
    """
    Build a controlled request plan:

    markets × keyword families × pages
    """
    selected = list(markets or MARKETS)
    plan: List[Dict[str, object]] = []
    for market in selected:
        for term in compact_queries_for_market(market, max_terms=max_terms):
            for page in range(1, pages_per_query + 1):
                plan.append(
                    {
                        "market": market,
                        "keywords": term,
                        "page": page,
                        "location": MARKET_LOCATIONS.get(market, market),
                    }
                )
    return plan
