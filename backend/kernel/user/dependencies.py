"""FastAPI dependency providers for C-02 (A6).

Provides:
- ``get_identity_user_service``: the published service singleton.
- ``get_db_session_factory``: the SQLAlchemy session factory.

Phase 5 (15.1): Support injecting SupabaseAuthClient into IdentityUserService
for C-02 admin propagation to Supabase Auth.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Lazy singleton — created on first use
_service = None
_session_factory: sessionmaker[Session] | None = None
# Optional SupabaseAuthClient for C-02 admin propagation (12.1)
_supabase_client = None


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


def get_identity_user_service():
    """Return the module-scoped service singleton (A6).

    Endpoints receive it via ``Depends(get_identity_user_service)``.
    Phase 5 (15.1): Injects SupabaseAuthClient if set.
    """
    global _service
    if _service is None:
        from kernel.user.services.service import IdentityUserService
        _service = IdentityUserService(
            session_factory=get_db_session_factory(),
            supabase_client=_supabase_client,  # Phase 5 (15.1)
        )
    return _service


def set_supabase_client(client) -> None:
    """Set the SupabaseAuthClient for C-02 admin propagation (15.1)."""
    global _supabase_client
    _supabase_client = client


def reset_service_singleton() -> None:
    """Reset the service singleton (for tests)."""
    global _service, _session_factory, _supabase_client
    _service = None
    _session_factory = None
    _supabase_client = None
