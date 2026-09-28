# Germany Job Hunter — Tasks

Use `[x]` for completed and `[ ]` for pending.

---

## PHASE 1 - Project setup

- [x] Inspect current directory
- [x] Create `PROJECT_SPEC.md`
- [x] Create `TASKS.md`
- [x] Create `README.md`
- [x] Create minimum project folder structure (`backend/`, `frontend/`)
- [x] Create backend dependency file (`backend/requirements.txt`)
- [x] Create frontend dependency file (`frontend/package.json`) and Vite/TS/Tailwind config stubs
- [x] Stop after Phase 1 (no scrapers, no full dashboard)

---

## PHASE 2 - Database

- [x] Define SQLAlchemy Job model with all required fields
- [x] Configure SQLite connection and session
- [x] Create tables / lightweight migration path
- [x] Add indexes useful for filters and duplicate checks
- [x] Add database health check (`GET /health/db`) and smoke test (`tests/test_database.py`)
- [x] Verified: `python tests/test_database.py` passed; `backend/data/jobs.db` created

---

## PHASE 3 - Job source architecture

- [x] Define common source interface / base adapter
- [x] Implement source registry so new sources can be added easily
- [x] Ensure one failing source does not crash full refresh
- [x] Stub adapters for Arbeitsagentur, Arbeitnow, GermanTechJobs (no aggressive scraping of blocked sites)
- [x] Add `NormalizedJob` shared data structure
- [x] Add source manager tests (`tests/test_source_manager.py`)
- [x] Verified: `python tests/test_source_manager.py` passed

---

## PHASE 4 - German + English search terms

- [x] Centralize category search terms (DE + EN)
- [x] Centralize entry-level keywords (DE + EN)
- [x] Provide `get_search_terms()` helper for source adapters (no live fetching yet)
- [x] Add search term tests (`tests/test_search_terms.py`)
- [x] Verified: `python tests/test_search_terms.py` passed

---

## PHASE 5 - Normalization

- [x] Normalize raw listings into the Job model
- [x] Detect job language (de / en / de/en / unknown)
- [x] Detect remote / hybrid / employment type
- [x] Detect German and English requirements
- [x] Detect experience level signals
- [x] Keep original descriptions unchanged
- [x] Source mappers for Arbeitsagentur, Arbeitnow, GermanTechJobs (no live fetching)
- [x] Add normalization tests (`tests/test_normalization.py`)
- [x] Verified: `python tests/test_normalization.py` passed

---

## PHASE 6 - Scoring

- [x] Implement rule-based match scoring only
- [x] Map score to categories (Sehr passend / Gut passend / Möglich / Weniger passend)
- [x] Produce human-readable match reasons for “Warum passt diese Stelle?”
- [x] Default scoring profile + future profile support
- [x] Integrate scoring into normalization (`apply_score`)
- [x] Add scoring tests (`tests/test_scoring.py`)
- [x] Verified: `python tests/test_scoring.py` passed (11 tests); all backend suites green

---

## PHASE 7 - Duplicate detection

- [x] Deduplicate by normalized company + title + location
- [x] Deduplicate by source_job_id
- [x] Deduplicate by job_url
- [x] Update `last_seen_at` for existing matches; insert only truly new jobs
- [x] Preserve application status on merge; keep extra sources via `JobSourceReference`
- [x] Add fingerprint + source-reference schema support
- [x] Add deduplication tests (`tests/test_deduplication.py`)
- [x] Verified: `python tests/test_deduplication.py` passed (8 tests); all backend suites green

---

## PHASE 8 - FastAPI

- [x] `GET /jobs` with filters
- [x] `GET /jobs/{id}`
- [x] `POST /jobs/refresh`
- [x] `PATCH /jobs/{id}/status`
- [x] `GET /stats`
- [x] `GET /sources`
- [x] CORS for local frontend
- [x] `GET /health` verifies database
- [x] Add API tests (`tests/test_api.py`)
- [x] Verified: all backend suites green; local `/health` returns ok

---

## PHASE 9 - Turkish frontend

- [x] Vite + React + TypeScript + Tailwind app shell
- [x] Dashboard header: Germany Job Hunter / Almanya İş İlanları
- [x] Statistics section (Turkish labels, `GET /stats`)
- [x] Filters (Turkish labels, backend query params)
- [x] Job table/actions + status updates via API
- [x] Job details modal including “Neden uygun?”
- [x] Refresh action and truthful source status display
- [x] Frontend typecheck + build verified

---

## PHASE 10 - Real Job Source Integration: Arbeitsagentur

- [x] Implement real Arbeitsagentur Jobsuche REST client/source
- [x] Configurable MVP refresh queries (`mvp_refresh_queries`)
- [x] Map → normalize → score → dedupe → SQLite via `POST /jobs/refresh`
- [x] Preserve application status on refresh
- [x] `GET /sources` reports Arbeitsagentur `implemented=true`
- [x] Unit tests with mocked HTTP (no live network in default suite)
- [x] Optional live test (`tests/live/test_arbeitsagentur_live.py`)
- [x] Docs updated (PROJECT_SPEC.md, README.md)
- [x] Verified live: 5–9 real jobs fetched/scored/stored; frontend build OK; backend suite green

---

## PHASE 11 - Real Job Source Integration: Arbeitnow

- [x] Implement real Arbeitnow public job-board API client/source
- [x] Germany filtering + target IT role filtering (reuse search/category config)
- [x] Controlled pagination (`ARBEITNOW_MAX_PAGES` / `ARBEITNOW_MAX_JOBS`)
- [x] Refresh runs Arbeitsagentur + Arbeitnow independently
- [x] Cross-source dedupe preserves status and source references
- [x] `GET /sources` reports Arbeitnow `implemented=true`
- [x] Unit/cross-source tests + optional live test
- [x] Frontend shows multi-source indicator; build verified
- [x] Docs updated (PROJECT_SPEC.md, README.md)

---

## Usability hardening (daily use)

- [x] Faster refresh: parallel sources, deduped queries, optional details off, sensible caps, per-source timings
- [x] Job list pagination (25/50/100) + page scrolling; all SQLite jobs reachable
- [x] Stats counters match DB score/status bands; cards apply filters
- [x] Source status reflects last real refresh (Aktif / Hata / Henüz eklenmedi / Devre dışı)
- [x] Source card CSS overflow fixed
- [x] Filters show “X ilan bulundu” and use exact match bands

## PHASE 12 - Additional real sources

- [x] Absolventa: sitemap + JobPosting JSON-LD (live verified)
- [x] Jobvector: documented unavailable (Cloudflare / partner API)
- [x] Make it in Germany: documented unavailable (BA channel only)
- [x] GermanTechJobs: documented unavailable (API deprecated)
- [x] EURES: public JSON search API, Germany filter (live verified)
- [x] Combined refresh + docs/tests updated

## Notes

- Do not add Docker, Redis, PostgreSQL, auth, paid AI APIs, auto-apply, schedulers, or cloud infra.
- Do not use fake jobs once real source integration begins.
- Update this file after completing each phase.
