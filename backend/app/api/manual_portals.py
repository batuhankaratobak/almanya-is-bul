"""Manual portal deep-link endpoints for hard-to-automate boards."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from app.services.manual_portals import build_manual_portal_links

router = APIRouter(tags=["manual-portals"])


@router.get(
    "/manual-portals",
    summary="Browser deep-links for StepStone/Indeed/LinkedIn/Glassdoor and local boards",
)
def get_manual_portals(
    markets: Optional[List[str]] = Query(None, description="DE,CH,FR,NL"),
) -> dict:
    return build_manual_portal_links(markets=markets)
