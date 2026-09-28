"""Apply-today queue: best unscored-pipeline jobs ready for application packages."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.cv_translate import detect_output_language
from app.services.ollama_client import ollama_status


def get_apply_queue(
    db: Session,
    *,
    limit: int = 10,
    min_score: int = 70,
) -> Dict[str, Any]:
    """
    Return top jobs ready to apply:
    - match_score >= min_score
    - status in new/reviewing (not applied/ignored/rejected/offer)
    - has a usable application URL
    """
    limit = max(1, min(int(limit), 30))
    min_score = max(0, min(int(min_score), 100))

    blocked = {"applied", "ignored", "rejected", "offer"}
    rows: List[Job] = (
        db.query(Job)
        .filter(Job.match_score >= min_score)
        .filter(or_(Job.status.is_(None), Job.status.notin_(list(blocked))))
        .order_by(Job.match_score.desc(), Job.id.desc())
        .limit(limit * 3)  # filter URL-less after
        .all()
    )

    items: List[Dict[str, Any]] = []
    for job in rows:
        url = (job.application_url or job.job_url or "").strip()
        if not url or url.startswith("about:"):
            continue
        lang = detect_output_language(
            job_language=job.job_language,
            title=job.title or "",
            description=job.description or "",
        )
        items.append(
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "match_score": job.match_score or 0,
                "match_category": job.match_category,
                "status": job.status or "new",
                "job_language": job.job_language,
                "suggested_lang": lang,
                "application_url": url,
                "source": job.source,
                "checklist": {
                    "lebenslauf": True,
                    "anschreiben": True,
                    "save_as_pdf": True,
                    "zeugnis_reminder": True,
                },
            }
        )
        if len(items) >= limit:
            break

    return {
        "min_score": min_score,
        "limit": limit,
        "total": len(items),
        "germany_essentials": germany_essentials(),
        "ollama": ollama_status(),
        "items": items,
    }


def germany_essentials() -> List[Dict[str, str]]:
    """Static checklist for a complete German Bewerbung package."""
    return [
        {
            "id": "lebenslauf",
            "title": "Lebenslauf (CV)",
            "detail": "İlana özel A4 Word CV indir; çoğu portal PDF ister → Word’de Farklı Kaydet → PDF.",
        },
        {
            "id": "anschreiben",
            "title": "Anschreiben (ön yazı)",
            "detail": "Almanya’da çoğu orta ölçekli işveren bekler. İlana özel Anschreiben indir.",
        },
        {
            "id": "zeugnisse",
            "title": "Zeugnisse / diploma",
            "detail": "Lisans diploması + varsa staj belgesi PDF’lerini hazır tut (app üretmez; sen yüklersin).",
        },
        {
            "id": "sprache",
            "title": "Dil seviyesi dürüst olsun",
            "detail": "CV’de Almanca/İngilizce seviyen abartılmasın; ilan B2+ istiyorsa dürüst yaz.",
        },
        {
            "id": "pdf",
            "title": "PDF paket",
            "detail": "İdeal: Anschreiben.pdf + Lebenslauf.pdf (+ Zeugnis). Tek PDF birleştirmek de yaygın.",
        },
        {
            "id": "foto",
            "title": "Fotoğraf (opsiyonel)",
            "detail": "Tech/startup’ta çoğu zaman gerekmez. Geleneksel ilan isterse profesyonel vesikalık ekle.",
        },
        {
            "id": "visa",
            "title": "Çalışma izni / vize notu",
            "detail": "İlan sorarsa: mevcut durumunu kısa ve net belirt (EU Blue Card hedefi vb.).",
        },
    ]
