# Germany Job Hunter — Project Specification

## Purpose

Local MVP application to find job listings across Germany using **German and English** search terms, store them locally in SQLite, remove duplicates, score relevance with rule-based logic, and display results in a **Turkish-language** dashboard.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite |

## Language Rules

- Visible UI / frontend: **Turkish**
- Search queries: German **and** English job titles (unchanged)
- Original job advertisements / descriptions: unchanged (keep source language)
- Detect job ad language: German, English, or mixed
- Code, variables, API routes, internal docs: English OK

## Target Job Categories

### Softwareentwicklung
Junior Softwareentwickler, Softwareentwickler Berufseinsteiger, Junior Entwickler, Anwendungsentwickler, Junior Frontend/Backend/Full Stack Entwickler, Junior Software Developer/Engineer, Graduate Software Engineer, Entry Level Software Developer, Junior Frontend/Backend/Full Stack Developer

### IT Support / Systemadministration
IT Support, IT Support Mitarbeiter, IT Administrator, Junior IT Administrator, Systemadministrator, Junior Systemadministrator, Fachinformatiker Systemintegration, IT Helpdesk, IT Servicedesk, Anwendersupport, Technischer Support, IT Support Specialist/Engineer, Technical Support Engineer, Application Support, Junior System Administrator

### Cybersecurity
IT Sicherheit, Informationssicherheit, Junior Informationssicherheit, Junior Cyber Security, SOC Analyst, Junior SOC Analyst, IT Security Analyst, Junior Cyber Security Analyst, Cybersecurity Analyst, Information Security Analyst, Junior Security Engineer, Junior IT Security Consultant

### QA / Testing
Softwaretester, Junior Softwaretester, Test Engineer, Junior Test Engineer, QA Engineer, Junior QA Engineer, Software Tester, QA Analyst

### IT Consulting / Application Support
Junior IT Consultant, IT Consultant Berufseinsteiger, Junior IT Berater, Anwendungsbetreuer, Junior Anwendungsbetreuer, Applikationsbetreuer, Junior ERP Consultant, IT Projektmitarbeiter, Application Support Engineer, Graduate IT Consultant, Junior Application Specialist

## Entry-Level Keywords

**German:** Junior, Berufseinsteiger, Absolvent, Berufseinstieg, Einstieg, Trainee  
**English:** Junior, Entry Level, Graduate, Early Career, Trainee

## Job Sources

### Sources

| Source | Status | Access |
|--------|--------|--------|
| Arbeitsagentur | **implemented** | Jobsuche REST API |
| Arbeitnow | **implemented** | Public job-board JSON API |
| Absolventa | **implemented** | Public sitemap + schema.org JobPosting JSON-LD |
| EURES | **implemented** | Public EURES JSON search API (`locationCodes=de`) |
| Jobvector | `not_implemented` | Cloudflare-protected; partner API only |
| Make it in Germany | `not_implemented` | No independent API (BA Jobsuche already covered) |
| GermanTechJobs | `not_implemented` | Public `/api/jobs` deprecated; SPA behind Cloudflare |

### Arbeitsagentur access method
Uses the publicly documented Jobsuche REST API (same endpoints used by the official job search service / documented via [bundesAPI/jobsuche-api](https://github.com/bundesAPI/jobsuche-api)):

1. Search: `GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs`
2. Details: `GET .../pc/v4/jobdetails/{base64(referenznummer)}`
3. Auth header: `X-API-Key: jobboerse-jobsuche` (public client id; overridable via `ARBEITSAGENTUR_API_KEY`)

**Request strategy**
- Germany-wide search by omitting `wo` / `umkreis`
- Controlled limits: `ARBEITSAGENTUR_MAX_RESULTS_PER_QUERY` (default 25), `ARBEITSAGENTUR_MAX_TOTAL_JOBS` (default 60)
- Timeout default 20s; concurrent searches (default 3) and optional concurrent detail fetches
- Detail fetch **off by default** (`ARBEITSAGENTUR_FETCH_DETAILS=false`) for daily refresh speed; search payload is enough for listing
- Known jobs with stored descriptions skip detail re-download when details are enabled
- Sources run in parallel so one slow source does not block others; per-source timings returned in refresh response

**Query strategy**
- Refresh uses limited `mvp_refresh_queries` from `backend/app/config/search_terms.json` (German + English representative terms across categories)
- Search terms are deduplicated before HTTP requests
- Does not send the entire search-term catalog on every refresh

**Job URL**
- `https://www.arbeitsagentur.de/jobsuche/jobdetail/{referenznummer}`

**Known limitations (Arbeitsagentur)**
- Unofficial/public client-id auth (not a private partner API contract); may change
- Search hits may lack full description; detail calls add latency/load
- Rate limits / temporary HTTP errors possible; source fails cleanly without crashing refresh

### Arbeitnow access method
Uses the free public job-board API (no API key):

`GET https://www.arbeitnow.com/api/job-board-api?page={n}`

**Request strategy**
- Paginated feed (not keyword search at API level)
- Limits: `ARBEITNOW_MAX_PAGES` (default 2), `ARBEITNOW_MAX_JOBS` (default 80)
- Timeout default 20s; runs in parallel with other sources; one failing source does not stop others

**Local filtering**
- Germany relevance via location/title/slug markers (cities, Deutschland/Germany, DE Remote)
- Target IT roles via existing `detect_role_category` + configured search terms
- Unrelated roles (e.g. warehouse, nurse) excluded before persistence

**Known limitations (Arbeitnow)**
- Feed is Europe/remote-oriented; Germany filter is heuristic (no geocoder)
- API page size is server-controlled; we only cap pages/total kept jobs

### Absolventa access method
No public keyword-search JSON API (employer Pull API is inbound only). Uses:

1. `GET https://www.absolventa.de/sitemap-stellen.xml`
2. Filter IT-relevant `/stellenangebote/...` URLs
3. Fetch schema.org `JobPosting` JSON-LD from detail pages

Limits: `ABSOLVENTA_MAX_JOBS` (default 25), `ABSOLVENTA_MAX_CANDIDATE_URLS` (default 40), detail concurrency 3.

### EURES access method
Public JSON API used by the EURES portal (no API key):

`POST https://europa.eu/eures/api/jv-searchengine/public/jv-search/search`

Germany via `locationCodes: ["de"]`. Limits: `EURES_MAX_RESULTS_PER_QUERY` (default 8), `EURES_MAX_TOTAL_JOBS` (default 40).

Job URL: `https://europa.eu/eures/portal/jv-se/jv-details/{id}`

### Unavailable sources (documented)
- **Jobvector** — site returns Cloudflare challenge; API is partner/customer only
- **Make it in Germany** — listings are a BA Jobsuche opt-in channel; no separate public feed
- **GermanTechJobs** — `/api/jobs` returns deprecated; no replacement structured feed without scraping behind Cloudflare

### Do not aggressively scrape
LinkedIn, Glassdoor, Indeed, StepStone, Cloudflare-protected boards

### Later (architecture must allow easy addition)
XING, Jobware, Stellenanzeigen.de, meinestadt.de, Kimeta, Joblift, Jooble, Yourfirm, INTERAMT

**Rule:** Do not claim a source works unless it has been tested. One failing source must not crash a full refresh.

## Job Model

| Field | Description |
|-------|-------------|
| id | Primary key |
| source | Source identifier |
| source_job_id | ID from source |
| title | Job title |
| company | Company name |
| location | Location |
| description | Original description (unchanged) |
| job_url | Link to listing |
| date_posted | Posted date from source |
| first_seen_at | First time seen locally |
| last_seen_at | Last time seen locally |
| remote | Remote flag |
| hybrid | Hybrid flag |
| employment_type | e.g. full-time, part-time |
| job_language | de / en / mixed |
| german_requirement | Detected German level requirement |
| english_requirement | Detected English requirement |
| experience_level | Detected experience level |
| match_score | 0–100 rule-based score |
| match_category | Score band label |
| status | Application status |
| created_at | Created timestamp |
| updated_at | Updated timestamp |

## Application Status

| Value | German UI |
|-------|-----------|
| new | Neu |
| reviewing | Prüfen |
| applied | Beworben |
| interview | Vorstellungsgespräch |
| rejected | Absage |
| ignored | Ignoriert |
| offer | Angebot |

## Match Scoring (Rule-Based Only)

No external AI API. Scoring is deterministic and implemented in `backend/app/services/scoring.py`.

### Base score
`base_score = 40`, then apply positive/negative rules. Final score is clamped to `0–100`.

Equivalent signals are counted once (e.g. Junior + Berufseinsteiger → one +25). Seniority penalties (Senior / Lead / Principal / Staff) are also applied once.

### Positive
| Points | Signal |
|--------|--------|
| +25 | Junior / Entry Level / Berufseinsteiger / Graduate / Absolvent (once) |
| +15 | Relevant IT role (target categories) |
| +10 | 0–2 years experience |
| +8 | 1–3 years experience |
| +10 | German B1 or B2 accepted |
| +10 | English accepted, or English-language job without conflicting mandatory German C1/C2 |
| +10 | Remote or Hybrid (once) |
| +5 | Relevant degree (Informatik, Computer Science, Computer Engineering, Software Engineering, Information Technology, Wirtschaftsinformatik) |
| +5 | Explicit trainee / graduate program |

### Negative
| Points | Signal |
|--------|--------|
| −25 | Senior / Lead / Principal / Staff Engineer (once) |
| −20 | 5+ years required |
| −15 | 4+ years required |
| −10 | 3+ years required |
| −20 | Mandatory German C1 |
| −25 | Mandatory German C2 |
| −15 | Explicit management responsibility |
| −10 | Role clearly outside target categories |

German “von Vorteil” / “wünschenswert” / preferred does **not** receive a C1/C2 penalty.

### Categories
| Score | Label |
|-------|-------|
| 85–100 | Sehr passend |
| 70–84 | Gut passend |
| 50–69 | Möglich |
| 0–49 | Weniger passend |

Do **not** exclude German- or English-language jobs.

### Default target profile (MVP)
Target categories: software_development, it_support, cybersecurity, qa_testing, system_administration, application_support, it_consulting. Preferred max German required: B2. Work models: remote, hybrid, onsite. A custom profile can be supplied later without changing the scoring API.

## Duplicate Detection

Normalize and compare:

1. `company + title + location`
2. `source_job_id`
3. `job_url`

Never show the same job multiple times in the UI.

## Dashboard UI (Turkish)

**Title:** Germany Job Hunter  
**Subtitle:** Almanya İş İlanları

### Statistics
- Toplam İlan
- Çok Uygun
- Uygun
- Olası
- Yeni
- Başvuruldu
- Mülakat
- Teklif

### Main action
İlanları Güncelle → `POST /jobs/refresh`

### Filters
Ara, İş Alanı, Uygunluk, Başvuru Durumu, Konum, İlan Dili, Almanca Seviyesi, Çalışma Modeli, Kaynak

### Category filter values
Tümü, Yazılım Geliştirme, IT Destek, Siber Güvenlik, QA / Test, Sistem Yönetimi, Uygulama Desteği, IT Danışmanlık

### Job list fields
Uygunluk Skoru, Pozisyon, Şirket, Konum, Kaynak, İlan Dili, Almanca Gereksinimi, Deneyim Seviyesi, Çalışma Modeli, Yayın Tarihi, Durum

### Row actions
İlanı Aç, Detaylar, Başvuruldu, İncele, Yoksay

### Job details
Pozisyon, Şirket, Konum, Orijinal İlan Açıklaması, Deneyim, Dil gereksinimleri, Çalışma modeli, Kaynak, Uygunluk, plus **Neden uygun?** with rule-based reasons (Turkish labels in UI).

### Refresh summary
Taranan İlan, Yeni İlan, Tekrarlanan, Güncellenen, Çok Uygun, kaynak durumları (ör. Hazır değil)

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | /jobs | List jobs (filters below) |
| GET | /jobs/{id} | Job detail |
| POST | /jobs/refresh | Manual refresh from sources |
| PATCH | /jobs/{id}/status | Update application status |
| GET | /stats | Dashboard statistics |
| GET | /sources | Source status list |

### GET /jobs query filters
`search`, `category`, `status`, `language`, `german_level`, `remote`, `source`, `min_score`, `location`

## Explicit Non-Goals (MVP)

Do **not** add:

- Docker, Redis, PostgreSQL
- Authentication
- Paid AI APIs
- Automatic job applications
- Background schedulers
- Cloud infrastructure
- Fake jobs after real source integration begins

## Project Layout (planned)

```
OTOMASYON/
├── README.md
├── PROJECT_SPEC.md
├── TASKS.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── api/
│   │   ├── sources/
│   │   ├── services/
│   │   └── db/
│   └── data/          # SQLite file location
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
```

## Development Principles

- Keep it simple; MVP first
- Do not overengineer
- One failing source must not crash full refresh
- Update `TASKS.md` after completing each phase
- Do not claim a source works unless tested
