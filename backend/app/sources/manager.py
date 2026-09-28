"""Source registry and resilient multi-source fetch orchestration."""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from concurrent.futures import as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.sources.base import JobSource
from app.sources.normalized_job import NormalizedJob

logger = logging.getLogger(__name__)

# One slow source must not hang the whole refresh indefinitely.
DEFAULT_SOURCE_TIMEOUT_SECONDS = float(os.getenv("SOURCE_FETCH_TIMEOUT_SECONDS") or 90)


def _dedupe_terms(search_terms: List[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for term in search_terms:
        normalized = (term or "").strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


@dataclass
class SourceFetchResult:
    """Per-source outcome for a refresh run."""

    status: str
    jobs_found: int = 0
    raw_jobs: int = 0
    accepted_jobs: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "status": self.status,
            "jobs_found": self.jobs_found,
            "raw_jobs": self.raw_jobs,
            "accepted_jobs": self.accepted_jobs,
            "duration_seconds": round(self.duration_seconds, 3),
        }
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass
class RefreshResult:
    """Aggregate result of fetching from all registered sources."""

    jobs: List[NormalizedJob] = field(default_factory=list)
    sources: Dict[str, SourceFetchResult] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def source_stats(self) -> Dict[str, Dict[str, object]]:
        return {name: result.to_dict() for name, result in self.sources.items()}


class SourceManager:
    """Register sources and fetch jobs without letting one failure stop others."""

    def __init__(
        self,
        *,
        max_source_workers: int = 3,
        source_timeout_seconds: Optional[float] = None,
    ) -> None:
        self._sources: Dict[str, JobSource] = {}
        self.max_source_workers = max(1, max_source_workers)
        self.source_timeout_seconds = float(
            source_timeout_seconds
            if source_timeout_seconds is not None
            else DEFAULT_SOURCE_TIMEOUT_SECONDS
        )

    def register(self, source: JobSource) -> None:
        if not source.name:
            raise ValueError("Source name must not be empty")
        if source.name in self._sources:
            raise ValueError(f"Source already registered: {source.name}")
        self._sources[source.name] = source

    def registered_sources(self) -> List[str]:
        return list(self._sources.keys())

    def get_sources(self) -> List[JobSource]:
        return list(self._sources.values())

    def fetch_all(self, search_terms: List[str]) -> RefreshResult:
        result = RefreshResult()
        terms = _dedupe_terms(search_terms)
        started = time.perf_counter()

        runnable: List[JobSource] = []
        for name, source in self._sources.items():
            if not source.enabled:
                result.sources[name] = SourceFetchResult(status="disabled", jobs_found=0)
                continue
            runnable.append(source)

        if runnable:
            workers = min(self.max_source_workers, len(runnable))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._fetch_one, source, terms): source.name
                    for source in runnable
                }
                for future in as_completed(futures):
                    name = futures[future]
                    fetch_result, jobs = future.result()
                    result.sources[name] = fetch_result
                    if jobs:
                        result.jobs.extend(jobs)
                    logger.info(
                        "Source %s finished in %.2fs status=%s jobs=%s",
                        name,
                        fetch_result.duration_seconds,
                        fetch_result.status,
                        fetch_result.jobs_found,
                    )

        ordered: Dict[str, SourceFetchResult] = {}
        for name in self._sources:
            if name in result.sources:
                ordered[name] = result.sources[name]
        result.sources = ordered
        result.duration_seconds = time.perf_counter() - started
        logger.info("Refresh fetch_all completed in %.2fs", result.duration_seconds)
        return result

    def _fetch_one(
        self, source: JobSource, search_terms: List[str]
    ) -> Tuple[SourceFetchResult, List[NormalizedJob]]:
        started = time.perf_counter()
        if not source.implemented:
            return (
                SourceFetchResult(
                    status="not_implemented",
                    jobs_found=0,
                    error="Reliable public automated access unavailable",
                    duration_seconds=0.0,
                ),
                [],
            )
        try:
            # HTTP clients already enforce per-request timeouts; this wall-clock
            # guard keeps a stuck source from blocking the whole refresh forever.
            with ThreadPoolExecutor(max_workers=1) as guard:
                guarded = guard.submit(source.fetch_jobs, search_terms)
                try:
                    jobs = guarded.result(timeout=self.source_timeout_seconds)
                except FuturesTimeoutError:
                    duration = time.perf_counter() - started
                    return (
                        SourceFetchResult(
                            status="failed",
                            jobs_found=0,
                            error=(
                                f"Source timed out after "
                                f"{self.source_timeout_seconds:.0f}s"
                            ),
                            duration_seconds=duration,
                        ),
                        [],
                    )
            if jobs is None:
                raise ValueError("fetch_jobs returned None")
            duration = time.perf_counter() - started
            count = len(jobs)
            raw = int(getattr(source, "last_raw_jobs", count) or count)
            accepted = int(getattr(source, "last_accepted_jobs", count) or count)
            return (
                SourceFetchResult(
                    status="success",
                    jobs_found=count,
                    raw_jobs=raw,
                    accepted_jobs=accepted,
                    duration_seconds=duration,
                ),
                list(jobs),
            )
        except NotImplementedError as exc:
            duration = time.perf_counter() - started
            return (
                SourceFetchResult(
                    status="not_implemented",
                    jobs_found=0,
                    error=str(exc) or "not implemented",
                    duration_seconds=duration,
                ),
                [],
            )
        except Exception as exc:  # noqa: BLE001 - isolate every source failure
            duration = time.perf_counter() - started
            return (
                SourceFetchResult(
                    status="failed",
                    jobs_found=0,
                    error=str(exc) or exc.__class__.__name__,
                    duration_seconds=duration,
                ),
                [],
            )
