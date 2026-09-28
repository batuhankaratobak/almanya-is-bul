"""Job source adapters and orchestration."""

from app.sources.absolventa import AbsolventaSource
from app.sources.arbeitsagentur import ArbeitsagenturSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import JobSource
from app.sources.eures import EuresSource
from app.sources.germantechjobs import GermanTechJobsSource
from app.sources.glassdoor import GlassdoorSource
from app.sources.jobicy import JobicySource
from app.sources.jobvector import JobvectorSource
from app.sources.jooble import JoobleSource
from app.sources.make_it_in_germany import MakeItInGermanySource
from app.sources.manager import RefreshResult, SourceFetchResult, SourceManager
from app.sources.normalized_job import NormalizedJob
from app.sources.remotive import RemotiveSource


def create_default_source_manager() -> SourceManager:
    """
    Germany-first personal job hunter sources.

    Live: Arbeitsagentur, Arbeitnow, Absolventa, EURES, Jobicy, Remotive,
    Jooble (when JOOBLE_API_KEY is set).
    Honest stubs: Make it in Germany, Jobvector, GermanTechJobs, Glassdoor.
    """
    manager = SourceManager(max_source_workers=5)
    manager.register(ArbeitsagenturSource())
    manager.register(ArbeitnowSource())
    manager.register(AbsolventaSource())
    manager.register(EuresSource())
    manager.register(JobicySource())
    manager.register(RemotiveSource())
    manager.register(JoobleSource())
    manager.register(MakeItInGermanySource())
    manager.register(JobvectorSource())
    manager.register(GermanTechJobsSource())
    manager.register(GlassdoorSource())
    return manager


__all__ = [
    "AbsolventaSource",
    "ArbeitsagenturSource",
    "ArbeitnowSource",
    "EuresSource",
    "GermanTechJobsSource",
    "GlassdoorSource",
    "JobicySource",
    "JobvectorSource",
    "JoobleSource",
    "MakeItInGermanySource",
    "RemotiveSource",
    "JobSource",
    "NormalizedJob",
    "RefreshResult",
    "SourceFetchResult",
    "SourceManager",
    "create_default_source_manager",
]
