"""Per-source daily request budget tracking (file-backed, local only)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.db import session as db_session


def _quota_path() -> Path:
    return Path(db_session.DATABASE_PATH).parent / "source_quota.json"


def _today() -> str:
    return date.today().isoformat()


def load_quota() -> Dict[str, Any]:
    path = _quota_path()
    if not path.exists():
        return {"day": _today(), "sources": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"day": _today(), "sources": {}}
    if not isinstance(payload, dict):
        return {"day": _today(), "sources": {}}
    if payload.get("day") != _today():
        return {"day": _today(), "sources": {}}
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    return {"day": _today(), "sources": sources}


def save_quota(payload: Dict[str, Any]) -> None:
    path = _quota_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_used(source: str) -> int:
    data = load_quota()
    entry = data["sources"].get(source) or {}
    return int(entry.get("requests") or 0)


def can_request(source: str, *, daily_limit: Optional[int]) -> bool:
    if daily_limit is None or daily_limit <= 0:
        return True
    return get_used(source) < daily_limit


def record_requests(source: str, count: int = 1) -> int:
    data = load_quota()
    entry = dict(data["sources"].get(source) or {})
    used = int(entry.get("requests") or 0) + max(0, count)
    entry["requests"] = used
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["sources"][source] = entry
    save_quota(data)
    return used


def remaining(source: str, *, daily_limit: Optional[int]) -> Optional[int]:
    if daily_limit is None or daily_limit <= 0:
        return None
    return max(0, daily_limit - get_used(source))
