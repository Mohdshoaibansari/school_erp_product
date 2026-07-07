"""TenantContext + FastAPI dependency (A6, task 7.2).

``TenantContext`` carries the request-scoped tenant identity: ``client_id``,
``institution_id``, ``user_id``, ``is_platform_owner``, and ``roles``.

The contextvar ``_tenant_context_var`` is set ONLY by the subdomain+JWT
middleware (task 7.1).  Endpoints access ``TenantContext`` via
``Depends(get_tenant_context)`` — the ONLY reader of the contextvar (A6
invariant, hard rule).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Sequence

from fastapi import Depends, HTTPException, Request

# The contextvar — set by middleware (7.1), read ONLY by get_tenant_context.
_tenant_context_var: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


@dataclass(frozen=True)
class TenantContext:
    """Request-scoped tenant identity (A6).

    Attributes:
        client_id: the Client (tenant) resolved from the subdomain (D3).
        institution_id: the institution selected by the in-app switcher (may be None).
        user_id: the Supabase Auth ``sub`` claim.
        is_platform_owner: whether the caller is a Platform Owner (D11).
        roles: the caller's role labels (e.g. ``["client_director"]``).
    """

    client_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None
    user_id: str | None = None
    is_platform_owner: bool = False
    roles: Sequence[str] = field(default_factory=list)


def set_tenant_context(ctx: TenantContext) -> None:
    """Set the contextvar. Called ONLY by the subdomain+JWT middleware (7.1)."""
    _tenant_context_var.set(ctx)


def get_tenant_context(request: Request) -> TenantContext:
    """FastAPI dependency — the ONLY reader of the contextvar (A6 invariant).

    Endpoints use ``Depends(get_tenant_context)``; they never touch the
    contextvar directly.
    """
    ctx = _tenant_context_var.get()
    if ctx is None:
        raise HTTPException(
            status_code=401,
            detail="Tenant context not set — middleware did not resolve the request",
        )
    return ctx


def require_platform_owner(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    """Dependency guard: Platform-Owner-only (D11). Use on platform-scoped routes."""
    if not ctx.is_platform_owner:
        raise HTTPException(
            status_code=403,
            detail="Platform Owner privileges required",
        )
    return ctx
