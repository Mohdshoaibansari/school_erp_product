"""SQLAlchemy 2.0 declarative base + engine setup for all platform models."""

from __future__ import annotations

import logging
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models (SQLAlchemy 2.0 style)."""
    pass


# ============================================================
# Engine setup
# ============================================================

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get the global sync engine. Created lazily on first use."""
    global _engine
    if _engine is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
        )
        _engine = create_engine(database_url, pool_pre_ping=True)
        logger.info("Created sync DB engine")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get the global sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a Session, close on completion."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
