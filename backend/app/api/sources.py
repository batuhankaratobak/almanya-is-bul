"""Registered job sources endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.jobs import SourceInfo, SourcesResponse
from app.services.refresh import list_registered_sources

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=SourcesResponse, summary="List registered sources")
def get_sources() -> SourcesResponse:
    sources = [SourceInfo(**item) for item in list_registered_sources()]
    return SourcesResponse(sources=sources)
