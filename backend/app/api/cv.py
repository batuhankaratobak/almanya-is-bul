"""CV profile and tailored A4 Word download endpoints."""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.apply_queue import get_apply_queue
from app.services.cover_letter_docx import build_cover_letter_docx_bytes
from app.services.cv_profile import load_cv_profile, refresh_german_translation, save_cv_profile
from app.services.job_query import get_job_or_none
from app.services.tailored_docx import build_tailored_docx_bytes

router = APIRouter(tags=["cv"])


@router.get("/cv-profile", summary="Get local CV narrative profile")
def get_cv_profile() -> Dict[str, Any]:
    return load_cv_profile()


@router.put("/cv-profile", summary="Save local CV narrative profile (EN source)")
def put_cv_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    return save_cv_profile(payload, translate=True)


@router.post(
    "/cv-profile/translate",
    summary="Re-translate English CV fields to German",
)
def translate_cv_profile() -> Dict[str, Any]:
    return refresh_german_translation()


@router.get(
    "/apply-queue",
    summary="Today's best jobs ready for Lebenslauf + Anschreiben + apply",
)
def apply_queue(
    limit: int = Query(10, ge=1, le=30),
    min_score: int = Query(70, ge=0, le=100),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return get_apply_queue(db, limit=limit, min_score=min_score)


@router.get(
    "/jobs/{job_id}/tailored-cv.docx",
    summary="Download A4 Word CV tailored to one job",
)
def download_tailored_cv(
    job_id: int,
    lang: Optional[Literal["auto", "en", "de"]] = Query(
        "auto",
        description="Output language: auto (from job), en, or de",
    ),
    db: Session = Depends(get_db),
) -> Response:
    job = get_job_or_none(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    override = None if lang in (None, "auto") else lang
    content, output_lang = build_tailored_docx_bytes(job, lang=override)
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", (job.title or "job")[:40]).strip("_")
    filename = f"CV_{output_lang}_{job_id}_{safe_title or 'application'}.docx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-CV-Language": output_lang,
        },
    )


@router.get(
    "/jobs/{job_id}/anschreiben.docx",
    summary="Download A4 Anschreiben / cover letter tailored to one job",
)
def download_anschreiben(
    job_id: int,
    lang: Optional[Literal["auto", "en", "de"]] = Query(
        "auto",
        description="Output language: auto (from job), en, or de",
    ),
    db: Session = Depends(get_db),
) -> Response:
    job = get_job_or_none(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    override = None if lang in (None, "auto") else lang
    content, output_lang = build_cover_letter_docx_bytes(job, lang=override)
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", (job.title or "job")[:40]).strip("_")
    filename = f"Anschreiben_{output_lang}_{job_id}_{safe_title or 'application'}.docx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-CV-Language": output_lang,
        },
    )
