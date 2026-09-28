"""FastAPI entrypoint for Germany Job Hunter."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load backend/.env before source adapters read API credentials.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.api import (
    cv_router,
    health_router,
    jobs_router,
    manual_portals_router,
    profile_router,
    sources_router,
    stats_router,
)
from app.db import init_db
from app.services.candidate_profile import load_profile
from app.services.cv_profile import load_cv_profile


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    load_profile()  # ensure default local profile exists
    load_cv_profile()  # ensure editable CV narrative exists
    yield


app = FastAPI(
    title="Germany Job Hunter",
    version="0.2.0",
    description="Local job hunter for DE/CH/FR/NL with profile-based scoring.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(stats_router)
app.include_router(sources_router)
app.include_router(manual_portals_router)
app.include_router(profile_router)
app.include_router(cv_router)
