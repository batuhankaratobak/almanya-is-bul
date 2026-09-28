"""Build browser deep-links for hard-to-automate job portals."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote_plus

from app.config.markets import MARKET_LABELS, MARKETS, compact_queries_for_market
from app.services.candidate_profile import load_profile

DEFAULT_QUERIES = (
    "Software Developer",
    "Junior Developer",
    "IT Support",
    "Application Support",
    "QA Tester",
    "System Administrator",
    "Cyber Security",
)


def _queries_from_profile(profile: Optional[Dict[str, Any]] = None) -> List[str]:
    data = profile if profile is not None else load_profile()
    roles = []
    if isinstance(data, dict):
        roles = [str(r).strip() for r in (data.get("target_roles") or []) if str(r).strip()]
    if not roles:
        roles = list(DEFAULT_QUERIES)
    # Keep compact — first 7 unique.
    seen = set()
    out: List[str] = []
    for role in roles:
        key = role.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(role)
        if len(out) >= 7:
            break
    return out


def build_manual_portal_links(
    *,
    markets: Sequence[str] | None = None,
    queries: Sequence[str] | None = None,
) -> Dict[str, Any]:
    selected_markets = [m for m in (markets or MARKETS) if m in MARKET_LABELS]
    terms = list(queries) if queries else _queries_from_profile()
    if not terms:
        terms = list(DEFAULT_QUERIES)

    portals = []
    for market in selected_markets:
        q = terms[0]
        encoded = quote_plus(q)
        location = {
            "DE": "Germany",
            "CH": "Switzerland",
            "FR": "France",
            "NL": "Netherlands",
        }[market]
        loc_enc = quote_plus(location)
        portals.extend(
            [
                {
                    "portal": "StepStone",
                    "market": market,
                    "label": f"StepStone ({MARKET_LABELS[market]})",
                    "query": q,
                    "url": _stepstone_url(market, encoded),
                },
                {
                    "portal": "Indeed",
                    "market": market,
                    "label": f"Indeed ({MARKET_LABELS[market]})",
                    "query": q,
                    "url": _indeed_url(market, encoded, loc_enc),
                },
                {
                    "portal": "LinkedIn",
                    "market": market,
                    "label": f"LinkedIn ({MARKET_LABELS[market]})",
                    "query": q,
                    "url": (
                        "https://www.linkedin.com/jobs/search/"
                        f"?keywords={encoded}&location={loc_enc}&f_TPR=r604800"
                    ),
                },
                {
                    "portal": "Glassdoor",
                    "market": market,
                    "label": f"Glassdoor ({MARKET_LABELS[market]})",
                    "query": q,
                    "url": (
                        "https://www.glassdoor.com/Job/jobs.htm"
                        f"?sc.keyword={encoded}&locKeyword={loc_enc}"
                    ),
                },
            ]
        )

        # Country-native manual surfaces for CORE sources without APIs.
        if market == "CH":
            portals.append(
                {
                    "portal": "jobs.ch",
                    "market": "CH",
                    "label": "jobs.ch",
                    "query": q,
                    "url": f"https://www.jobs.ch/en/vacancies/?term={encoded}",
                }
            )
            portals.append(
                {
                    "portal": "SwissDevJobs",
                    "market": "CH",
                    "label": "SwissDevJobs",
                    "query": q,
                    "url": f"https://swissdevjobs.ch/?query={encoded}",
                }
            )
        elif market == "FR":
            portals.append(
                {
                    "portal": "Welcome to the Jungle",
                    "market": "FR",
                    "label": "Welcome to the Jungle",
                    "query": q,
                    "url": f"https://www.welcometothejungle.com/en/jobs?query={encoded}&around=France",
                }
            )
        elif market == "NL":
            portals.append(
                {
                    "portal": "Nationale Vacaturebank",
                    "market": "NL",
                    "label": "Nationale Vacaturebank",
                    "query": q,
                    "url": f"https://www.nationalevacaturebank.nl/vacature/zoeken?query={encoded}",
                }
            )
            portals.append(
                {
                    "portal": "Magnet.me",
                    "market": "NL",
                    "label": "Magnet.me",
                    "query": q,
                    "url": f"https://magnet.me/jobs?query={encoded}",
                }
            )
        elif market == "DE":
            portals.append(
                {
                    "portal": "Make it in Germany",
                    "market": "DE",
                    "label": "Make it in Germany",
                    "query": q,
                    "url": (
                        "https://www.make-it-in-germany.com/en/working-in-germany/"
                        f"job-listings?tx_solr%5Bq%5D={encoded}"
                    ),
                }
            )

    return {
        "queries": terms,
        "markets": selected_markets,
        "keyword_families": compact_queries_for_market("DE", max_terms=10),
        "portals": portals,
    }


def _stepstone_url(market: str, encoded_query: str) -> str:
    hosts = {
        "DE": "https://www.stepstone.de/jobs/",
        "CH": "https://www.stepstone.ch/jobs/",
        "FR": "https://www.stepstone.fr/jobs/",
        "NL": "https://www.stepstone.nl/jobs/",
    }
    base = hosts.get(market, hosts["DE"])
    return f"{base}{encoded_query}"


def _indeed_url(market: str, encoded_query: str, encoded_location: str) -> str:
    hosts = {
        "DE": "https://de.indeed.com",
        "CH": "https://ch.indeed.com",
        "FR": "https://fr.indeed.com",
        "NL": "https://nl.indeed.com",
    }
    host = hosts.get(market, hosts["DE"])
    return f"{host}/jobs?q={encoded_query}&l={encoded_location}&fromage=7"
