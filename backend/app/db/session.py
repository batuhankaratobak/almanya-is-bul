"""SQLite engine, session factory, and initialization."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

# Import models so metadata is registered before create_all.
from app.models import job as _job_model  # noqa: F401
from app.models import job_source_reference as _job_source_reference_model  # noqa: F401

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_DEFAULT_DB_PATH = DATA_DIR / "jobs.db"


def _resolve_database_path() -> Path:
    env_path = os.getenv("JOBS_DB_PATH")
    if env_path:
        return Path(env_path)
    return _DEFAULT_DB_PATH


DATABASE_PATH = _resolve_database_path()
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def configure_database(database_path: Optional[Path] = None) -> Path:
    """Reconfigure the global SQLite engine (used by API tests)."""
    global DATABASE_PATH, DATABASE_URL, engine, SessionLocal

    DATABASE_PATH = Path(database_path) if database_path is not None else _resolve_database_path()
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return DATABASE_PATH


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> Path:
    """Create the data directory and all tables. Returns the SQLite file path."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
    return DATABASE_PATH


def _ensure_sqlite_columns() -> None:
    """Add newly introduced columns on existing SQLite databases (no migration framework)."""
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    statements = []
    if "fingerprint" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN fingerprint VARCHAR(64)")
    if "role_family" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN role_family VARCHAR(64)")
    if "discovery_relevance" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN discovery_relevance VARCHAR(16)")
    if "classification_json" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN classification_json TEXT")
    if "country" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN country VARCHAR(8) DEFAULT 'DE'")
    if "application_url" not in columns:
        statements.append("ALTER TABLE jobs ADD COLUMN application_url VARCHAR(1024)")
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_jobs_fingerprint ON jobs (fingerprint)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_jobs_source_job_id ON jobs (source_job_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_jobs_role_family ON jobs (role_family)")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_jobs_discovery_relevance "
                "ON jobs (discovery_relevance)"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_jobs_country ON jobs (country)")
        )


def check_db_connection() -> dict:
    """Run a simple connection check against SQLite."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "ok": True,
        "database": str(DATABASE_PATH),
        "exists": DATABASE_PATH.exists(),
    }
