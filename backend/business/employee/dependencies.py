"""Employee module — dependencies."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from business.employee.services.service import EmployeeService

_service: EmployeeService | None = None


def get_employee_service() -> EmployeeService:
    global _service
    if _service is None:
        database_url = os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres"
        )
        engine = create_engine(database_url)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        _service = EmployeeService(session_factory=session_factory)
    return _service


def reset_employee_service() -> None:
    global _service
    _service = None
