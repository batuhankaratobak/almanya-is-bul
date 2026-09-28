"""Application status values for job tracking."""

from __future__ import annotations

from enum import Enum


class ApplicationStatus(str, Enum):
    """Stored status values (English). UI labels are German."""

    NEW = "new"
    REVIEWING = "reviewing"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    IGNORED = "ignored"
    OFFER = "offer"


STATUS_LABELS_DE: dict[ApplicationStatus, str] = {
    ApplicationStatus.NEW: "Neu",
    ApplicationStatus.REVIEWING: "Prüfen",
    ApplicationStatus.APPLIED: "Beworben",
    ApplicationStatus.INTERVIEW: "Vorstellungsgespräch",
    ApplicationStatus.REJECTED: "Absage",
    ApplicationStatus.IGNORED: "Ignoriert",
    ApplicationStatus.OFFER: "Angebot",
}
