"""pytest fixtures for C-01 tests.

Session-scoped: ensures the local Supabase Postgres is available, resets the
schema, and applies Alembic migrations. Provides a synchronous DB engine and
session factory for tests.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
)

# Tables that hold seed data (should NOT be cleaned between tests)
_SEED_TABLES = {"legal_entity_type", "org_unit_type", "institution_type_name"}

# All C-01 entity tables in reverse dependency order for cleanup
_C01_TABLES = [
    "ownership_transfer_event",
    "institution_lifecycle_event",
    "client_lifecycle_event",
    "approval",
    "org_unit",
    "institution",
    "institution_type",
    "client",
]


def _ensure_supabase_running() -> None:
    """Ensure the local Supabase stack is running (start if needed)."""
    try:
        result = subprocess.run(
            ["supabase", "status"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        if result.returncode != 0:
            subprocess.run(
                ["supabase", "start", "--ignore-health-check"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(__file__)),
                timeout=180,
            )
    except FileNotFoundError:
        pass  # Supabase CLI not available — assume DB is already running


def _reset_database() -> None:
    """Reset the database by dropping and recreating the public schema,
    then applying Alembic migrations from scratch.
    """
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Drop and recreate public schema to get a clean state
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        # Grant permissions (Supabase default)
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()
    engine.dispose()

    # Apply migrations from scratch
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Session-scoped DB engine. Resets the database before the session."""
    _ensure_supabase_running()
    _reset_database()
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    """Session factory bound to the test engine."""
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def db_session(db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Per-test DB session. Deletes all non-seed data after each test."""
    session = db_session_factory()
    yield session
    # Clean up all non-seed data so tests start from a clean state
    # (some RLS tests commit, so rollback alone is insufficient)
    session.rollback()
    # Set platform owner to bypass RLS during cleanup (FORCE RLS is on)
    session.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
    for table_name in _C01_TABLES:
        session.execute(text(f"DELETE FROM {table_name}"))
    session.commit()
    session.close()
