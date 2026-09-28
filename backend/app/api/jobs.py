"""Job listing, detail, status update, and refresh endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.status import ApplicationStatus
from app.schemas.jobs import JobListResponse, JobOut, JobStatusUpdate, RefreshResponse
from app.services.job_query import get_job_or_none, list_jobs, serialize_job, update_job_status
from app.services.refresh import refresh_jobs

router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List jobs with filters and pagination",
)
def get_jobs(
    search: Optional[str] = Query(None, description="Search title, company, description"),
    category: Optional[str] = Query(None),
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    language: Optional[str] = Query(None),
    german_level: Optional[str] = Query(None),
    work_model: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    location: Optional[str] = Query(None),
    country: Optional[str] = Query(None, description="DE, CH, FR, NL, EU"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("score"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    try:
        items, total = list_jobs(
            db,
            search=search,
            category=category,
            status=status_filter.value if status_filter else None,
            language=language,
            german_level=german_level,
            work_model=work_model,
            source=source,
            min_score=min_score,
            max_score=max_score,
            location=location,
            country=country,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return JobListResponse(items=items, total=total, limit=min(limit, 200), offset=offset)


@router.get(
    "/jobs/{job_id}",
    response_model=JobOut,
    summary="Get a single job by id",
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = get_job_or_none(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return serialize_job(db, job)


@router.patch(
    "/jobs/{job_id}/status",
    response_model=JobOut,
    summary="Update application status for a job",
)
def patch_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
) -> JobOut:
    job = get_job_or_none(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    updated = update_job_status(db, job, payload.status.value)
    return serialize_job(db, updated)


@router.post(
    "/jobs/refresh",
    response_model=RefreshResponse,
    summary="Refresh jobs from registered sources",
)
def post_jobs_refresh(db: Session = Depends(get_db)) -> RefreshResponse:
    """
    Runs the source manager. Sources run concurrently; one failure never
    crashes the whole refresh. Per-source timings are included in the response.
    """
    return refresh_jobs(db)
