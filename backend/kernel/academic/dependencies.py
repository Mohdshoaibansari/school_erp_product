"""C-05 Academic Structure — dependencies (FastAPI DI)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from kernel.db import get_db
from kernel.academic.services.service import AcademicService


def get_academic_service(db: Session = Depends(get_db)) -> AcademicService:
    """Dependency for AcademicService."""
    return AcademicService(db)
