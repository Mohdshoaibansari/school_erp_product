"""C-04 Authorization — FastAPI dependencies (D5, D7, D10, D12, D13, D22, D31).

Provides:
- ``get_enforcer()`` — the global Casbin enforcer singleton.
- ``require_permission(resource, action, ...)`` — FastAPI dependency for
authorization checks.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, HTTPException, Request

from kernel.tenant_context import TenantContext, get_tenant_context

_enforcer: Any = None


def set_enforcer(enforcer: Any) -> None:
    """Store the global Casbin enforcer singleton (called by app factory)."""
    global _enforcer
    _enforcer = enforcer


def get_enforcer() -> Any:
    """Return the global Casbin enforcer singleton (D10, 5.2).

    Injected via ``Depends(get_enforcer)``. Returns the instance set by the
    app factory during ``create_app()``.
    """
    return _enforcer


def require_permission(
    resource: str,
    action: str,
    *,
    owner_id: uuid.UUID | None = None,
):
    """FastAPI dependency: enforce Casbin role+scope + optional ownership check.

    Usage:
        @router.post("/institutions")
        def create(..., _ = Depends(require_permission("institution", "create"))):
            ...

    Scope data (client_id, institution_id) is taken from ``TenantContext`` —
    the endpoint's own client/institution is used as the object's scope.
    This is correct for the majority of endpoints (same-tenant operations)
    per D19.

    Returns a dependency closure that reads ``TenantContext`` and the Casbin
    enforcer, then:
      1. Casbin role+scope check — does the user's role have this permission
         at the given scope (tenant/institution)?
      2. Ownership check — if ``owner_id`` is provided and doesn't match the
         current user, verifies the user has admin scope to bypass.

    Raises ``HTTPException(403)`` on denial.
    """

    def _enforce(
        ctx: TenantContext = Depends(get_tenant_context),
        enforcer: Any = Depends(get_enforcer),
    ):
        if enforcer is None:
            raise HTTPException(status_code=500, detail="Authorization service not available")

        roles = ctx.roles or []

        # Platform owner bypass (D28) — check BEFORE role validation
        if ctx.is_platform_owner or "platform_owner" in roles:
            return

        if not roles:
            raise HTTPException(status_code=403, detail="Permission denied — no roles assigned")

        # Build Casbin subject from TenantContext
        sub = {
            "role": roles[0],
            "client_id": str(ctx.client_id) if ctx.client_id else "",
            "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
        }

        # Build Casbin object — use TenantContext values (D19: endpoint
        # passes what it knows; for same-tenant operations, the object
        # inherits the user's client/institution scope)
        obj = {
            "name": resource,
            "client_id": str(ctx.client_id) if ctx.client_id else "",
            "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
        }

        # Step 1: Casbin role+scope check (D12)
        if not enforcer.enforce(sub, obj, action):
            raise HTTPException(status_code=403, detail="Permission denied")

        # Step 2: Ownership check (D22)
        if owner_id is not None and ctx.user_id and str(ctx.user_id) != str(owner_id):
            # Check if user has admin scope to bypass ownership
            admin_obj = {"name": resource, "client_id": "", "institution_id": ""}
            if not enforcer.enforce(sub, admin_obj, action):
                raise HTTPException(status_code=403, detail="You can only access your own resource")

    return _enforce
