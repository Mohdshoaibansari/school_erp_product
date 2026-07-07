"""FastAPI dependency providers for C-01 (A6).

Provides:
- ``get_tenant_institution_service``: the published service singleton.
- ``get_db_session_factory``: the SQLAlchemy session factory.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from kernel.tenant_institution.services import TenantInstitutionService

# Lazy singleton — created on first use
_service: TenantInstitutionService | None = None
_session_factory: sessionmaker[Session] | None = None


def _get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
    )


def get_db_session_factory() -> sessionmaker[Session]:
    """Return the module-scoped session factory singleton (A6)."""
    global _session_factory
    if _session_factory is None:
        engine = create_engine(_get_database_url())
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory


def get_tenant_institution_service() -> TenantInstitutionService:
    """Return the module-scoped service singleton (A6).

    Endpoints receive it via ``Depends(get_tenant_institution_service)``.
    """
    global _service
    if _service is None:
        _service = TenantInstitutionService(
            session_factory=get_db_session_factory(),
        )
    return _service


def reset_service_singleton() -> None:
    """Reset the service singleton (for tests)."""
    global _service, _session_factory
    _service = None
    _session_factory = None
