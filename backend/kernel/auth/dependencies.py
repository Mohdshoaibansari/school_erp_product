"""FastAPI dependency providers for C-03 (A6).

Provides:
- ``get_supabase_auth_client``: the Supabase Auth client singleton.
- ``get_auth_service``: the AuthService singleton (Phase 2+).
"""

from __future__ import annotations

from kernel.auth.supabase_client import SupabaseAuthClient, create_supabase_auth_client

# Lazy singleton — created on first use
_supabase_client: SupabaseAuthClient | None = None


def get_supabase_auth_client() -> SupabaseAuthClient:
    """Return the module-scoped Supabase Auth client singleton (A6, D21, D22).

    Endpoints receive it via ``Depends(get_supabase_auth_client)``.
    Created from SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_supabase_auth_client()
    return _supabase_client


def set_supabase_auth_client(client: SupabaseAuthClient) -> None:
    """Set the Supabase Auth client (for tests)."""
    global _supabase_client
    _supabase_client = client


def reset_supabase_auth_client() -> None:
    """Reset the Supabase Auth client singleton (for tests)."""
    global _supabase_client
    _supabase_client = None
