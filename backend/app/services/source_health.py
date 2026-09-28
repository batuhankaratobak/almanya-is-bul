"""Persist last refresh health so GET /sources can reflect reality."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.db import session as db_session

RECENT_SUCCESS_HOURS = 168  # 7 days


def _health_path() -> Path:
    # Keep health next to the active SQLite file so tests stay isolated.
    return Path(db_session.DATABASE_PATH).parent / "source_health.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_health() -> Dict[str, Dict[str, Any]]:
    path = _health_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(name): value
        for name, value in payload.items()
        if isinstance(value, dict)
    }


def save_health(entries: Dict[str, Dict[str, Any]]) -> None:
    path = _health_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_refresh_health(source_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Merge latest refresh source stats into persistent health."""
    current = load_health()
    stamped = _now_iso()
    for name, stats in source_stats.items():
        status = str(stats.get("status") or "failed")
        entry = {
            "status": status,
            "jobs_found": int(stats.get("jobs_found") or 0),
            "raw_jobs": int(stats.get("raw_jobs") or stats.get("jobs_found") or 0),
            "accepted_jobs": int(
                stats.get("accepted_jobs") or stats.get("jobs_found") or 0
            ),
            "error": stats.get("error"),
            "duration_seconds": stats.get("duration_seconds"),
            "updated_at": stamped,
        }
        if status == "success":
            entry["last_success_at"] = stamped
        elif name in current and current[name].get("last_success_at"):
            entry["last_success_at"] = current[name]["last_success_at"]
        current[name] = entry
    save_health(current)
    return current


def resolve_display_status(
    *,
    name: str,
    enabled: bool,
    implemented: bool,
    health: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """
    Map source + health into API status:
    active | error | not_implemented | disabled | idle

    Aktif only when a real successful fetch is recorded.
    Stale health saying not_implemented must not override code that is implemented.
    """
    if not enabled:
        return "disabled"
    if not implemented:
        return "not_implemented"

    health = health if health is not None else load_health()
    entry = health.get(name) or {}
    last_status = entry.get("status")
    # Ignore obsolete health rows that contradict the live source class.
    if last_status in {"not_implemented", "disabled"}:
        last_status = None

    if last_status == "failed":
        return "error"
    # Aktif when a real request has successfully completed (and not later failed).
    if last_status == "success" or entry.get("last_success_at"):
        return "active"
    return "idle"


def _is_recent(iso_value: Optional[str]) -> bool:
    if not iso_value:
        return False
    try:
        stamp = datetime.fromisoformat(iso_value)
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
    return age.total_seconds() <= RECENT_SUCCESS_HOURS * 3600
