"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.db import check_db_connection
from app.services.ollama_client import ollama_status

router = APIRouter(tags=["health"])


@router.get("/health", summary="Backend and database health check")
def health() -> dict:
    try:
        check_db_connection()
        return {"status": "ok", "database": "ok", "ollama": ollama_status()}
    except Exception:  # noqa: BLE001
        return {"status": "ok", "database": "error", "ollama": ollama_status()}
