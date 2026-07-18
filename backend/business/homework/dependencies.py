"""Homework module — dependencies."""

from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from business.homework.services.service import HomeworkService
from kernel.audit import DefaultAuditEmitter

_service: HomeworkService | None = None

def get_homework_service() -> HomeworkService:
    global _service
    if _service is None:
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        engine = create_engine(db_url)
        sf = sessionmaker(bind=engine, expire_on_commit=False)
        _service = HomeworkService(session_factory=sf, audit_emitter=DefaultAuditEmitter())
    return _service

def reset_homework_service() -> None:
    global _service; _service = None
