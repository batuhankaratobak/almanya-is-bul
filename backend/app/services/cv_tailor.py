"""Pick CV sections automatically from a job description (ATS-oriented)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


_TOKEN_RE = re.compile(r"[a-z0-9+#./-]{2,}", re.I)

# Job focus → boost phrases (EN + DE) used when ranking experiences/projects/skills.
_FOCUS_SIGNALS: Dict[str, Tuple[str, ...]] = {
    "it_support": (
        "it support",
        "help desk",
        "helpdesk",
        "servicedesk",
        "service desk",
        "desktop support",
        "1st level",
        "first level",
        "first-level",
        "systemadmin",
        "system admin",
        "systemadministrator",
        "windows",
        "active directory",
        "group policy",
        "hardware",
        "printer",
        "netzwerk",
        "network",
        "benutzer",
        "anwender",
        "it-support",
        "it support",
        "support mitarbeiter",
        "support-mitarbeiter",
        "edv",
        "microsoft 365",
        "office 365",
        "outlook",
        "teams",
        "troubleshooting",
        "störung",
        "stoerung",
        "ticket",
    ),
    "software": (
        "software",
        "developer",
        "entwickler",
        "entwicklung",
        "backend",
        "frontend",
        "fullstack",
        "full-stack",
        "full stack",
        "python",
        "fastapi",
        "react",
        "typescript",
        "javascript",
        "node.js",
        "nodejs",
        "api",
        "sql",
        "postgresql",
        "sqlite",
        "git",
        "docker",
        "softwareentwickler",
        "webentwickler",
        "programmier",
    ),
    "mobile": (
        "mobile",
        "android",
        "ios",
        "react native",
        "expo",
        "capacitor",
        "swift",
        "kotlin",
        "app entwickler",
        "app-entwickler",
        "mobil",
    ),
    "realtime": (
        "websocket",
        "socket.io",
        "real-time",
        "realtime",
        "echtzeit",
        "multiplayer",
        "next.js",
        "nextjs",
        "frontend",
        "dashboard",
        "ssr",
    ),
    "data_research": (
        "excel",
        "openpyxl",
        "scraping",
        "datenanalyse",
        "data analysis",
        "research",
        "crm",
        "erp",
        "vertrieb",
        "sales",
        "b2b",
        "lead",
    ),
    "vision": (
        "opencv",
        "mediapipe",
        "computer vision",
        "bildverarbeitung",
        "accessibility",
        "barrierefreiheit",
        "assistive",
    ),
}

_FOCUS_PROJECT_HINTS: Dict[str, Tuple[str, ...]] = {
    "it_support": (
        "inventory",
        "envanter",
        "deployment",
        "windows",
        "job hunter",
        "bk works",
    ),
    "software": (
        "job hunter",
        "quickchess",
        "airport",
        "next.js",
        "inventory",
        "gaze",
        "göz takip",
        "bk works",
    ),
    "mobile": ("yasak", "taboo", "balık", "balik", "react native", "capacitor", "airport"),
    "realtime": ("quickchess", "socket", "chess", "airport", "next.js"),
    "data_research": ("bk works", "dealer", "job hunter", "excel"),
    "vision": ("gaze", "göz", "mediapipe", "opencv"),
}

_FOCUS_EXPERIENCE_HINTS: Dict[str, Tuple[str, ...]] = {
    "it_support": (
        "it intern",
        "municipality",
        "belediye",
        "bilgi işlem",
        "help desk",
        "deployment",
    ),
    "software": ("it intern", "sales specialist", "germany"),
    "mobile": (),
    "realtime": (),
    "data_research": ("sales", "germany", "cw", "tommatech", "erp", "crm"),
    "vision": (),
}

_HEADLINES = {
    "en": {
        "it_support": "Computer Engineer | IT Support & Systems",
        "software": "Computer Engineer | Junior Software Developer",
        "mobile": "Computer Engineer | Mobile / Frontend Developer",
        "realtime": "Computer Engineer | Full-Stack / Real-Time Developer",
        "data_research": "Computer Engineer | B2B Tools & IT Operations",
        "vision": "Computer Engineer | Python / Computer Vision",
        "general": "Computer Engineer | IT Support & Junior Software",
    },
    "de": {
        "it_support": "Computeringenieur | IT-Support & Systeme",
        "software": "Computeringenieur | Junior Softwareentwickler",
        "mobile": "Computeringenieur | Mobile-/Frontend-Entwicklung",
        "realtime": "Computeringenieur | Full-Stack / Echtzeit",
        "data_research": "Computeringenieur | B2B-Tools & IT-Betrieb",
        "vision": "Computeringenieur | Python / Computer Vision",
        "general": "Computeringenieur | IT-Support & Junior Software",
    },
}

_SUMMARY_LEAD = {
    "en": {
        "it_support": (
            "For this role I highlight hands-on IT support: Windows deployment, "
            "hardware/software troubleshooting, basic networking, Help Desk tickets "
            "and Microsoft 365."
        ),
        "software": (
            "For this role I highlight software delivery: Python/FastAPI, React/TypeScript, "
            "SQL databases, APIs, Git and end-to-end product building with tests."
        ),
        "mobile": (
            "For this role I highlight mobile/product work: offline-first apps, "
            "TypeScript, React Native/Expo or Capacitor packaging, and QA automation."
        ),
        "realtime": (
            "For this role I highlight real-time full-stack work: Node.js, Socket.IO, "
            "server-authoritative logic, reconnection handling and production deployment."
        ),
        "data_research": (
            "For this role I highlight operational tooling: Help Desk/ERP/CRM workflows, "
            "Python automation, Excel delivery and structured research pipelines."
        ),
        "vision": (
            "For this role I highlight Python desktop/CV work: OpenCV/MediaPipe pipelines, "
            "signal processing, accessibility-minded UX and thorough unit testing."
        ),
        "general": (
            "For this application I combine municipal IT support experience with "
            "practical software projects relevant to the posting."
        ),
    },
    "de": {
        "it_support": (
            "Für diese Stelle stelle ich praktischen IT-Support in den Vordergrund: "
            "Windows-Deployment, Hardware-/Software-Troubleshooting, Basisnetzwerk, "
            "Helpdesk-Tickets und Microsoft 365."
        ),
        "software": (
            "Für diese Stelle stelle ich Software-Umsetzung in den Vordergrund: "
            "Python/FastAPI, React/TypeScript, SQL-Datenbanken, APIs, Git und "
            "End-to-End-Produktentwicklung mit Tests."
        ),
        "mobile": (
            "Für diese Stelle stelle ich Mobile-/Produktarbeit in den Vordergrund: "
            "Offline-First-Apps, TypeScript, React Native/Expo oder Capacitor sowie QA-Automation."
        ),
        "realtime": (
            "Für diese Stelle stelle ich Full-Stack-/Echtzeit-Arbeit in den Vordergrund: "
            "Node.js, Socket.IO, serverseitige Spiellogik, Reconnect und produktives Deployment."
        ),
        "data_research": (
            "Für diese Stelle stelle ich operative Tools in den Vordergrund: "
            "Helpdesk-/ERP-/CRM-Prozesse, Python-Automatisierung, Excel-Lieferung und Research-Pipelines."
        ),
        "vision": (
            "Für diese Stelle stelle ich Python-Desktop-/CV-Arbeit in den Vordergrund: "
            "OpenCV/MediaPipe, Signalverarbeitung, barrierefreie UX und gründliche Unit-Tests."
        ),
        "general": (
            "Für diese Bewerbung kombiniere ich kommunale IT-Support-Erfahrung mit "
            "praxisnahen Softwareprojekten, die zur Stellenausschreibung passen."
        ),
    },
}


@dataclass
class TailoredSelection:
    focus: str
    headline: str
    summary: str
    skills: List[str]
    other_skills: List[str]
    experiences: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    requirement_lines: List[str]


def tailor_cv_for_job(
    profile: Dict[str, Any],
    *,
    title: str,
    description: str,
    lang: str,
) -> TailoredSelection:
    """Return a job-specific slice of the CV profile for Word generation."""
    lang = "de" if lang == "de" else "en"
    jd = f"{title}\n{description}"
    focus = detect_job_focus(jd)
    matched_skills, other_skills = rank_skills(profile.get("skills") or [], jd, focus=focus)
    experiences = rank_blocks(
        profile.get("experiences") or [],
        jd,
        focus=focus,
        kind="experience",
    )
    projects = rank_blocks(
        profile.get("projects") or [],
        jd,
        focus=focus,
        kind="project",
    )

    exp_n, proj_n = _section_counts(focus)
    experiences = experiences[:exp_n]
    projects = projects[:proj_n]

    # Re-rank bullets inside selected blocks.
    experiences = [
        {
            **exp,
            "bullets": rank_texts(list(exp.get("bullets") or []), jd)[:4],
        }
        for exp in experiences
    ]
    projects = [
        {
            **proj,
            "bullets": rank_texts(list(proj.get("bullets") or []), jd)[:3],
        }
        for proj in projects
    ]

    headline = _HEADLINES[lang].get(focus) or _HEADLINES[lang]["general"]
    summary = compose_summary(
        base_summary=str(profile.get("summary") or ""),
        title=title,
        matched_skills=matched_skills,
        focus=focus,
        lang=lang,
    )

    return TailoredSelection(
        focus=focus,
        headline=headline,
        summary=summary,
        skills=matched_skills[:14],
        other_skills=[s for s in other_skills if s not in matched_skills][:8],
        experiences=experiences,
        projects=projects,
        requirement_lines=build_fit_points(
            matched_skills=matched_skills,
            focus=focus,
            lang=lang,
            limit=3,
        ),
    )


def detect_job_focus(jd_text: str) -> str:
    blob = (jd_text or "").casefold()
    scores = {key: 0 for key in _FOCUS_SIGNALS}
    for focus, phrases in _FOCUS_SIGNALS.items():
        for phrase in phrases:
            if phrase in blob:
                scores[focus] += 2 if " " in phrase or "-" in phrase else 1
    # Title-weighted extras
    title = blob.split("\n", 1)[0]
    for focus, phrases in _FOCUS_SIGNALS.items():
        for phrase in phrases[:8]:
            if phrase in title:
                scores[focus] += 3
    best = max(scores.items(), key=lambda item: item[1])
    if best[1] <= 0:
        return "general"
    return best[0]


def rank_skills(
    skills: Sequence[str],
    jd_text: str,
    *,
    focus: str,
) -> Tuple[List[str], List[str]]:
    jd_low = (jd_text or "").casefold()
    jd_tokens = _tokens(jd_text)
    focus_phrases = _FOCUS_SIGNALS.get(focus, ())
    scored: List[Tuple[int, str]] = []
    for skill in skills:
        s = str(skill).strip()
        if not s:
            continue
        low = s.casefold()
        score = len(_tokens(s) & jd_tokens)
        if low in jd_low:
            score += 4
        elif any(tok in jd_low for tok in _tokens(s) if len(tok) > 3):
            score += 1
        if any(p in low or low in p for p in focus_phrases):
            score += 2
        scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1].casefold()))
    matched = [s for score, s in scored if score > 0]
    all_skills = [s for _, s in scored]
    if not matched:
        # Focus-biased fallback instead of random order.
        return all_skills[:10], all_skills
    return matched, all_skills


def rank_blocks(
    blocks: Sequence[Dict[str, Any]],
    jd_text: str,
    *,
    focus: str,
    kind: str,
) -> List[Dict[str, Any]]:
    jd_tokens = _tokens(jd_text)
    jd_low = (jd_text or "").casefold()
    hints = (
        _FOCUS_PROJECT_HINTS.get(focus, ())
        if kind == "project"
        else _FOCUS_EXPERIENCE_HINTS.get(focus, ())
    )

    def score_block(block: Dict[str, Any]) -> int:
        name = str(block.get("name") or block.get("title") or "")
        org = str(block.get("org") or "")
        stack = " ".join(str(x) for x in (block.get("stack") or []))
        bullets = " ".join(str(x) for x in (block.get("bullets") or []))
        blob = f"{name}\n{org}\n{stack}\n{bullets}"
        score = len(_tokens(blob) & jd_tokens)
        low = blob.casefold()
        for phrase in hints:
            if phrase in low:
                score += 6
        # Direct stack hits against JD
        for item in block.get("stack") or []:
            token = str(item).casefold()
            if token and token in jd_low:
                score += 3
        return score

    return sorted(list(blocks), key=score_block, reverse=True)


def rank_texts(texts: Sequence[str], jd_text: str) -> List[str]:
    jd_tokens = _tokens(jd_text)
    scored = [(_score_text(t, jd_tokens), t) for t in texts if str(t).strip()]
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    # Keep original relative order for zero-score ties already handled by len
    return [t for _, t in scored]


def extract_requirement_lines(description: str, *, limit: int = 5) -> List[str]:
    """Legacy helper kept for tests; Word CV uses build_fit_points instead."""
    _ = description
    return build_fit_points(matched_skills=[], focus="general", lang="en", limit=limit)


def build_fit_points(
    *,
    matched_skills: Sequence[str],
    focus: str,
    lang: str,
    limit: int = 3,
) -> List[str]:
    """
    Short, clean fit bullets written from the candidate side.

    Avoid pasting raw job-ad fragments (they often read poorly on a CV).
    """
    lang = "de" if lang == "de" else "en"
    skills = [str(s).strip() for s in matched_skills if str(s).strip()]
    top = skills[:4]
    skill_bit = ", ".join(top) if top else ""

    templates = {
        "en": {
            "it_support": [
                "Practical IT support experience with Windows, hardware/software troubleshooting and user assistance.",
                "Familiar with Help Desk workflows, Microsoft 365 and basic networking (TCP/IP, DNS, DHCP, LAN).",
                "Built automation that speeds up PC setup and inventory tracking in real IT environments.",
            ],
            "software": [
                "Hands-on software delivery with Python, JavaScript/TypeScript, React and SQL-backed APIs.",
                "Comfortable building end-to-end tools: backend services, web UIs, Git workflow and testing.",
                "Computer Engineering graduate focused on junior software / product engineering roles.",
            ],
            "mobile": [
                "Built offline-first mobile prototypes with TypeScript, React Native/Expo and Capacitor packaging.",
                "Strong product sense for mobile UX, local data storage and QA automation.",
                "Computer Engineering graduate targeting junior mobile / frontend engineering roles.",
            ],
            "realtime": [
                "Experience with real-time full-stack systems using Node.js, Socket.IO and server-side validation.",
                "Comfortable with reconnection handling, deployment and production-oriented testing.",
                "Computer Engineering graduate focused on junior full-stack / real-time roles.",
            ],
            "data_research": [
                "Operational experience with Help Desk, ERP and CRM workflows in a Germany-facing role.",
                "Built Python research/automation tools with Excel delivery, caching and structured data cleanup.",
                "Combines IT operations background with practical software tooling for business teams.",
            ],
            "vision": [
                "Built Python desktop/computer-vision pipelines with OpenCV, MediaPipe and careful on-device processing.",
                "Focus on reliability, accessibility-minded interaction and thorough unit testing.",
                "Computer Engineering graduate targeting junior Python / applied ML-adjacent roles.",
            ],
            "general": [
                "Computer Engineering graduate with municipal IT support experience and practical software projects.",
                "Strong mix of troubleshooting, automation, SQL databases and end-to-end product building.",
                "Looking for junior IT support, system support or entry-level software roles in Germany.",
            ],
            "skills": "Directly relevant skills for this role: {skills}.",
        },
        "de": {
            "it_support": [
                "Praktische IT-Support-Erfahrung mit Windows, Hardware-/Software-Troubleshooting und Anwenderhilfe.",
                "Vertraut mit Helpdesk-Prozessen, Microsoft 365 und Basisnetzwerk (TCP/IP, DNS, DHCP, LAN).",
                "Automatisierung für PC-Setup und Inventarprozesse in realen IT-Umgebungen umgesetzt.",
            ],
            "software": [
                "Praktische Softwareumsetzung mit Python, JavaScript/TypeScript, React und SQL-basierten APIs.",
                "End-to-End-Tools gebaut: Backend-Services, Web-UIs, Git-Workflow und Tests.",
                "Absolvent der Computer Engineering / Informatik mit Fokus auf Junior-Softwarerollen.",
            ],
            "mobile": [
                "Offline-First-Mobile-Prototypen mit TypeScript, React Native/Expo und Capacitor umgesetzt.",
                "Stark in Mobile-UX, lokaler Datenspeicherung und QA-Automatisierung.",
                "Absolvent der Computer Engineering / Informatik mit Fokus auf Mobile-/Frontend-Rollen.",
            ],
            "realtime": [
                "Erfahrung mit Echtzeit-Full-Stack-Systemen (Node.js, Socket.IO, serverseitige Validierung).",
                "Sicher im Umgang mit Reconnect, Deployment und praxisnahen Tests.",
                "Absolvent der Computer Engineering / Informatik mit Fokus auf Full-Stack-/Echtzeit-Rollen.",
            ],
            "data_research": [
                "Operative Erfahrung mit Helpdesk-, ERP- und CRM-Prozessen in einer Deutschland-bezogenen Rolle.",
                "Python-Research-/Automatisierungstools mit Excel-Export, Caching und Datenbereinigung gebaut.",
                "Kombiniert IT-Betriebserfahrung mit praktischen Software-Tools für Business-Teams.",
            ],
            "vision": [
                "Python-Desktop-/Computer-Vision-Pipelines mit OpenCV und MediaPipe umgesetzt.",
                "Fokus auf Zuverlässigkeit, barrierearme Interaktion und gründliche Unit-Tests.",
                "Absolvent der Computer Engineering / Informatik mit Fokus auf Python-/CV-Rollen.",
            ],
            "general": [
                "Absolvent der Computer Engineering / Informatik mit kommunaler IT-Support-Erfahrung und Softwareprojekten.",
                "Starke Kombination aus Troubleshooting, Automatisierung, SQL-Datenbanken und Produktumsetzung.",
                "Ziel: Junior IT-Support, System-Support oder Einstiegsrollen in der Softwareentwicklung in Deutschland.",
            ],
            "skills": "Direkt passende Kenntnisse für diese Stelle: {skills}.",
        },
    }

    pack = templates[lang]
    points = list(pack.get(focus) or pack["general"])
    if skill_bit:
        points.insert(0, str(pack["skills"]).format(skills=skill_bit))
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for point in points:
        key = point.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(point)
        if len(out) >= limit:
            break
    return out


def compose_summary(
    *,
    base_summary: str,
    title: str,
    matched_skills: Sequence[str],
    focus: str,
    lang: str,
) -> str:
    """Job-angled lead + short base summary. No meta/system phrasing."""
    _ = (title, matched_skills)
    lead = _SUMMARY_LEAD[lang].get(focus) or _SUMMARY_LEAD[lang]["general"]
    base = base_summary.strip()
    if len(base) > 220:
        base = base[:217].rsplit(" ", 1)[0] + "…"
    if not base:
        return lead
    return f"{lead} {base}"


def _section_counts(focus: str) -> Tuple[int, int]:
    # experiences, projects — A4 budget
    if focus == "it_support":
        return 3, 2
    if focus in {"software", "realtime", "vision", "mobile"}:
        return 2, 3
    if focus == "data_research":
        return 3, 2
    return 2, 2


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def _score_text(text: str, jd_tokens: set[str]) -> int:
    return len(_tokens(text) & jd_tokens)
