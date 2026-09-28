"""Per-source incremental refresh cursors (file-backed, local only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.db import session as db_session


def _cursor_path() -> Path:
    return Path(db_session.DATABASE_PATH).parent / "source_cursors.json"


def load_cursors() -> Dict[str, Any]:
    path = _cursor_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_cursors(payload: Dict[str, Any]) -> None:
    path = _cursor_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_cursor(source: str) -> Dict[str, Any]:
    data = load_cursors()
    entry = data.get(source) or {}
    return entry if isinstance(entry, dict) else {}


def get_last_seen_at(source: str) -> Optional[datetime]:
    raw = get_cursor(source).get("last_seen_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def update_cursor(
    source: str,
    *,
    last_seen_at: Optional[datetime] = None,
    last_ids: Optional[list[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = load_cursors()
    entry = dict(data.get(source) or {})
    if last_seen_at is not None:
        entry["last_seen_at"] = last_seen_at.astimezone(timezone.utc).isoformat()
    if last_ids is not None:
        entry["last_ids"] = list(last_ids)[:200]
    if extra:
        entry.update(extra)
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    data[source] = entry
    save_cursors(data)
    return entry
