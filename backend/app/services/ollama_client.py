"""Local Ollama HTTP client (optional). Falls back silently if offline."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"


def _host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")


def _model() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL


def ollama_enabled() -> bool:
    flag = (os.getenv("OLLAMA_ENABLED") or "true").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def ollama_status() -> Dict[str, Any]:
    """UI/API status: running, model name, available models."""
    host = _host()
    wanted = _model()
    if not ollama_enabled():
        return {
            "enabled": False,
            "running": False,
            "model": wanted,
            "models": [],
            "detail": "Kapalı (OLLAMA_ENABLED=false).",
        }
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{host}/api/tags")
        response.raise_for_status()
        payload = response.json()
        names = [str(m.get("name") or "") for m in (payload.get("models") or [])]
        has_model = any(wanted in name or name.startswith(wanted.split(":")[0]) for name in names)
        return {
            "enabled": True,
            "running": True,
            "model": wanted,
            "model_ready": has_model,
            "models": names,
            "detail": (
                "Hazır — CV/Anschreiben ilana göre yeniden yazılır."
                if has_model
                else f"Ollama açık ama model yok. Terminal: ollama pull {wanted}"
            ),
        }
    except Exception:  # noqa: BLE001
        return {
            "enabled": True,
            "running": False,
            "model": wanted,
            "model_ready": False,
            "models": [],
            "detail": "Ollama kapalı. Kuruluysa: ollama serve",
        }


def chat_json(
    *,
    system: str,
    user: str,
    timeout: float = 90.0,
) -> Optional[Dict[str, Any]]:
    """Return parsed JSON object from Ollama, or None on any failure."""
    if not ollama_enabled():
        return None
    status = ollama_status()
    if not status.get("running") or not status.get("model_ready"):
        return None
    host = _host()
    model = _model()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{host}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
        response.raise_for_status()
        content = ((response.json() or {}).get("message") or {}).get("content") or ""
        return _parse_json_object(content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama chat failed: %s", exc)
        return None


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None
