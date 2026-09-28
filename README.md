# Germany Job Hunter

Local AI-assisted job-search app for **Germany** (DE-first).

Collects listings from multiple public sources, normalizes and deduplicates them, scores fit against your profile, and helps you apply faster with an applications tracker plus **per-job A4 Word CVs** and cover letters.

This public version is designed to ship without personal data. Local profile files, source cache files, API keys and the SQLite job database are generated on your machine and ignored by Git.

UI language: **Turkish**. Job descriptions stay in their original language (DE/EN).

## Features

- Multi-source refresh into a local SQLite database
- Normalization, deduplication, role taxonomy, rule-based profile scoring
- Filters, job detail view, status workflow (`new` → `reviewing` → `applied` → …)
- Quick apply: open listing URL and mark as applied
- Applications panel for tracking active pipeline
- Manual deep-links for portals without a usable public API
- Editable CV narrative profile (write once in English)
- Auto German translation of CV narrative fields
- Tailored one-page A4 `.docx` download per job (section labels + content follow job language)
- Optional local AI rewriting with Ollama for CV summaries, fit points and cover letters
- Rule-based fallback when Ollama is not installed or the selected model is unavailable

## Tech stack

| Layer | Stack |
|-------|--------|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Documents | `python-docx` (A4 Word) |
| Translation | `deep-translator` (EN → DE, cached on profile) |
| Local AI | Ollama HTTP API (optional, default model `llama3.2:3b`) |

## Architecture (short)

```
Sources → Normalize → Role classify → Profile score → Dedup → SQLite
                                                              ↓
                                                         FastAPI
                                                              ↓
                                                      React dashboard
```

No auth, no cloud DB, no auto-apply, no CAPTCHA bypass.

## Job sources

| Source | Status | Notes |
|--------|--------|-------|
| Arbeitsagentur | Live | Public Jobsuche REST API |
| Arbeitnow | Live | Public job-board API |
| Absolventa | Live | Sitemap + JobPosting JSON-LD |
| EURES | Live | Public JSON search (`locationCodes=["de"]`) |
| Jobicy | Live | Remote/IT feed (filtered) |
| Remotive | Live | Remote feed (filtered) |
| Jooble | Live when keyed | Set `JOOBLE_API_KEY` in `backend/.env` (DE market) |
| Make it in Germany | Stub | No independent public API |
| Jobvector | Stub | Partner/Cloudflare-gated |
| GermanTechJobs | Stub | Public API deprecated |
| Glassdoor | Stub | Manual deep-link only |

Refresh uses keyword sets from `backend/app/config/search_terms.json`.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

Optional env:

| Variable | Purpose |
|----------|---------|
| `JOOBLE_API_KEY` | Enables Jooble DE searches |
| `JOOBLE_MARKETS` | Default `DE` |
| `OLLAMA_ENABLED` | Enables/disables local AI rewriting |
| `OLLAMA_HOST` | Default `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Default `llama3.2:3b` |
| `ARBEITSAGENTUR_*` | Jobsuche tuning (page size, caps, concurrency) |
| `ARBEITNOW_*` / `ABSOLVENTA_*` / `EURES_*` | Per-source caps and timeouts |

### Optional local AI

AI support is local-first. The app calls Ollama on your own machine and falls back to deterministic CV/cover-letter generation when Ollama is off.

```bash
ollama pull llama3.2:3b
ollama serve
```

To disable AI rewriting:

```env
OLLAMA_ENABLED=false
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173 (Vite proxies `/api` → `:8000`).

### Refresh jobs

```bash
curl -X POST http://127.0.0.1:8000/jobs/refresh
```

Or use **İlanları Güncelle** in the UI.

### CV profile & tailored Word

1. Open **Ayarlar** → fill the A4 CV form in **English**
2. Save → German translation is generated/cached automatically
3. On a job → **A4 Word** downloads `CV_en_…` or `CV_de_…` based on job language
4. Optional: `POST /cv-profile/translate` to force re-translate

Profile file: `backend/data/cv_profile.json` (generated locally, ignored by Git).

## Project layout

```
OTOMASYON/
├── README.md
├── PROJECT_SPEC.md
├── TASKS.md
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── config/       # search terms, markets, quotas
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/     # scoring, CV, Word, queries
│   │   └── sources/      # adapters + SourceManager
│   ├── data/             # local SQLite/profile/cache files; ignored except .gitkeep
│   ├── tests/
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/
        ├── services/
        └── types/
```

## Design choices

- **Germany-first:** most multi-country job APIs need a public website for keys; DE sources are usable now
- **Honest stubs:** sources without a clean public path stay visible but not faked
- **No auto-apply:** open the real listing; you submit yourself
- **ATS-friendly Word:** single-column A4, standard headings, bullets, no tables/graphics; skills/projects re-ranked against each job description

## Explicit non-goals

No Docker, Redis, PostgreSQL, authentication, paid AI core pipeline, automatic applications, background schedulers, or SaaS redesign in this local-first tool.

## License / privacy

Public-safe repository: no personal CV/profile data, no API keys, and no job database should be committed.

Runtime data stays on your machine:

- `backend/.env`
- `backend/data/jobs.db`
- `backend/data/candidate_profile.json`
- `backend/data/cv_profile.json`
- `backend/data/source_*.json`

German translation uses `deep-translator`, which may call an external translation service. Ollama rewriting is local when configured.
