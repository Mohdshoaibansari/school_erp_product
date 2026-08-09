"""FastAPI dependency providers for C-02 (A6).

Provides:
- ``get_identity_user_service``: the published service singleton.
- ``get_db_session_factory``: the SQLAlchemy session factory.

Phase 5 (15.1): Support injecting SupabaseAuthClient into IdentityUserService
for C-02 admin propagation to Supabase Auth.
"""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker, Session
from kernel.db import get_engine

# Lazy singleton — created on first use
_service = None
_session_factory: sessionmaker[Session] | None = None
# Optional SupabaseAuthClient for C-02 admin propagation (12.1)
_supabase_client = None


def get_db_session_factory() -> sessionmaker[Session]:
    """Return the module-scoped session factory singleton (A6)."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory


def get_identity_user_service():
    """Return the module-scoped UserService singleton (A6).

    Returns a UserService with StrategyResolver wired in.
    Endpoints receive it via ``Depends(get_identity_user_service)``.
    """
    global _service
    if _service is None:
        from kernel.user.services.service import UserService
        from kernel.user.services.strategies.cd_strategy import CDStrategy
        from kernel.user.services.strategies.institution_strategy import InstitutionUserStrategy
        from kernel.user.services.strategies.resolver import StrategyResolver

        session_factory = get_db_session_factory()

        cd_strategy = CDStrategy(
            session_factory=session_factory,
            supabase_client=_supabase_client,
        )
        institution_strategy = InstitutionUserStrategy(
            session_factory=session_factory,
            supabase_client=_supabase_client,
        )
        resolver = StrategyResolver(
            cd_strategy=cd_strategy,
            institution_strategy=institution_strategy,
            session_factory=session_factory,
        )
        _service = UserService(
            session_factory=session_factory,
            supabase_client=_supabase_client,
            resolver=resolver,
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
