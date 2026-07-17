"""Fees module — dependencies (D16)."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from business.fees.services.service import FeesService
from kernel.audit import DefaultAuditEmitter

_service: FeesService | None = None


def get_fees_service() -> FeesService:
    global _service
    if _service is None:
        database_url = os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        )
        engine = create_engine(database_url)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        _service = FeesService(session_factory=session_factory, audit_emitter=DefaultAuditEmitter())
    return _service


def reset_fees_service() -> None:
    global _service
    _service = None
