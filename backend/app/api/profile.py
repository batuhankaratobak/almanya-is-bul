"""Single local candidate profile endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.candidate_profile import get_default_profile, load_profile, save_profile
from app.services.rescore import rescore_all_jobs

router = APIRouter(tags=["profile"])


class CandidateProfileIn(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    target_categories: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience_areas: List[str] = Field(default_factory=list)
    education: str = ""
    german_level: str = "B1"
    english_level: str = "B2"
    preferred_max_experience_years: int = 2
    preferred_work_models: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    unwanted_roles: List[str] = Field(default_factory=list)


class CandidateProfileOut(CandidateProfileIn):
    pass


class ProfileSaveResponse(BaseModel):
    profile: CandidateProfileOut
    rescore: Dict[str, Any]


@router.get("/profile", response_model=CandidateProfileOut, summary="Get local candidate profile")
def get_profile() -> CandidateProfileOut:
    return CandidateProfileOut(**load_profile())


@router.get("/profile/default", response_model=CandidateProfileOut, summary="Default profile template")
def get_profile_default() -> CandidateProfileOut:
    return CandidateProfileOut(**get_default_profile())


@router.put("/profile", response_model=ProfileSaveResponse, summary="Save profile and rescore jobs")
def put_profile(payload: CandidateProfileIn, db: Session = Depends(get_db)) -> ProfileSaveResponse:
    saved = save_profile(payload.model_dump())
    result = rescore_all_jobs(db, profile=saved)
    return ProfileSaveResponse(profile=CandidateProfileOut(**saved), rescore=result)
