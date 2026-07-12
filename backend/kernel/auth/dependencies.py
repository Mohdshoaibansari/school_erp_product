"""FastAPI dependency providers for C-03 (A6).

Provides:
- ``get_supabase_auth_client``: the Supabase Auth client singleton.
- ``get_auth_service``: the AuthService singleton.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from kernel.auth.supabase_client import SupabaseAuthClient, create_supabase_auth_client
from kernel.auth.services.service import AuthService
from kernel.audit import DefaultAuditEmitter

# Lazy singleton — created on first use
_supabase_client: SupabaseAuthClient | None = None
_auth_service: AuthService | None = None


def get_supabase_auth_client() -> SupabaseAuthClient:
    """Return the module-scoped Supabase Auth client singleton (A6, D21, D22).

    Endpoints receive it via ``Depends(get_supabase_auth_client)``.
    Created from SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_supabase_auth_client()
    return _supabase_client


def get_auth_service() -> AuthService:
    """Return the AuthService singleton (A6, 10.1).

    Injects SupabaseAuthClient, session_factory, audit_emitter.
    Endpoints receive it via ``Depends(get_auth_service)``.
    """
    global _auth_service
    if _auth_service is None:
        supabase_client = get_supabase_auth_client()
        # Create session factory from DATABASE_URL env var
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
        )
        engine = create_engine(database_url)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        audit_emitter = DefaultAuditEmitter()
        _auth_service = AuthService(
            supabase_client=supabase_client,
            session_factory=session_factory,
            audit_emitter=audit_emitter,
        )
    return _auth_service


def set_supabase_auth_client(client: SupabaseAuthClient) -> None:
    """Set the Supabase Auth client (for tests)."""
    global _supabase_client
    _supabase_client = client


def set_auth_service(service: AuthService) -> None:
    """Set the AuthService singleton (for tests)."""
    global _auth_service
    _auth_service = service


def reset_supabase_auth_client() -> None:
    """Reset the Supabase Auth client singleton (for tests)."""
    global _supabase_client
    _supabase_client = None


def reset_auth_service() -> None:
    """Reset the AuthService singleton (for tests)."""
    global _auth_service
    _auth_service = None
