"""API routers."""

from app.api.cv import router as cv_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.manual_portals import router as manual_portals_router
from app.api.profile import router as profile_router
from app.api.sources import router as sources_router
from app.api.stats import router as stats_router

__all__ = [
    "cv_router",
    "health_router",
    "jobs_router",
    "manual_portals_router",
    "profile_router",
    "sources_router",
    "stats_router",
]
