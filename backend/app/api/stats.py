"""Dashboard statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.jobs import StatsResponse
from app.services.job_query import compute_stats

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse, summary="Dashboard statistics")
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    return StatsResponse(**compute_stats(db))
