"""C-04 Authorization — FastAPI dependencies (D5, D7, D10, D12, D13, D19, D22, D31).

Provides:
- ``get_enforcer()`` — the global Casbin enforcer singleton.
- ``require_permission(resource, action, ...)`` — FastAPI dependency for
  authorization checks. Accepts ``obj_client_id`` and ``obj_institution_id``
  for ABAC enforcement (D7, D19).
- ``check_permission(ctx, enforcer, resource, action, ...)`` — callable for
  inline ABAC checks after fetching a resource.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)

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


def _check_impl(
    ctx: TenantContext,
    enforcer: Any,
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> None:
    """Core authorization logic shared by require_permission and check_permission."""
    if enforcer is None:
        logger.error("[AUTHZ] Enforcer not available")
        raise HTTPException(status_code=500, detail="Authorization service not available")

    roles = ctx.roles or []

    # Platform owner bypass (D28) — check BEFORE role validation
    if ctx.is_platform_owner or "platform_owner" in roles:
        logger.debug("[AUTHZ] Platform owner bypass: resource=%s action=%s", resource, action)
        return

    if not roles:
        logger.warning("[AUTHZ] No roles assigned: user=%s resource=%s action=%s", ctx.user_id, resource, action)
        raise HTTPException(status_code=403, detail="Permission denied — no roles assigned")

    # Self-access bypass (D13): if owner_id matches the current user, allow without Casbin
    if owner_id is not None and ctx.user_id and str(ctx.user_id) == str(owner_id):
        logger.debug("[AUTHZ] Self-access bypass: user=%s resource=%s action=%s", ctx.user_id, resource, action)
        return

    # Build Casbin subject from TenantContext
    sub = {
        "role": roles[0],
        "client_id": str(ctx.client_id) if ctx.client_id else "",
        "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
    }

    # Build Casbin object — use explicit object attributes when provided (D7, D19),
    # fall back to ctx values for backward compatibility
    obj = {
        "name": resource,
        "client_id": str(obj_client_id) if obj_client_id is not None
                     else (str(ctx.client_id) if ctx.client_id else ""),
        "institution_id": str(obj_institution_id) if obj_institution_id is not None
                          else (str(ctx.institution_id) if ctx.institution_id else ""),
    }

    # Step 1: Casbin role+scope check (D12)
    if not enforcer.enforce(sub, obj, action):
        logger.warning("[AUTHZ] Permission denied: user=%s roles=%s resource=%s action=%s",
                       ctx.user_id, roles, resource, action)
        raise HTTPException(status_code=403, detail="Permission denied")

    logger.debug("[AUTHZ] Permission granted: user=%s roles=%s resource=%s action=%s",
                 ctx.user_id, roles, resource, action)

    # Step 2: Ownership check (D22)
    if owner_id is not None and ctx.user_id and str(ctx.user_id) != str(owner_id):
        # Check if user has admin scope to bypass ownership
        # Use ctx IDs so scoped policies (tenant/institution) can match
        admin_obj = {
            "name": resource,
            "client_id": str(ctx.client_id) if ctx.client_id else "",
            "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
        }
        if not enforcer.enforce(sub, admin_obj, action):
            raise HTTPException(status_code=403, detail="You can only access your own resource")


def check_permission(
    ctx: TenantContext,
    enforcer: Any,
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> None:
    """Check authorization inline (for use after fetching a resource).

    Usage in routes:
        institution = svc.get(institution_id)
        check_permission(ctx, enforcer, "institution", "read",
            obj_client_id=institution.client_id,
            obj_institution_id=institution.id)

    Raises HTTPException(403) on denial.
    """
    _check_impl(
        ctx, enforcer, resource, action,
        obj_client_id=obj_client_id,
        obj_institution_id=obj_institution_id,
        owner_id=owner_id,
    )


def require_permission(
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
):
    """FastAPI dependency: enforce Casbin role+scope + optional ownership check.

    Usage:
        @router.post("/institutions")
        def create(..., _ = Depends(require_permission("institution", "create"))):
            ...

        @router.get("/institutions")
        def list(..., _ = Depends(require_permission("institution", "list",
                    obj_client_id=ctx.client_id))):
            ...

    Object attributes (obj_client_id, obj_institution_id) are passed explicitly
    by the calling endpoint for ABAC enforcement (D7, D19). When not provided,
    falls back to TenantContext values (backward compatible).

    Returns a dependency closure that reads ``TenantContext`` and the Casbin
    enforcer, then enforces role+scope+ownership.

    Raises ``HTTPException(403)`` on denial.
    """

    def _enforce(
        ctx: TenantContext = Depends(get_tenant_context),
        enforcer: Any = Depends(get_enforcer),
    ):
        _check_impl(
            ctx, enforcer, resource, action,
            obj_client_id=obj_client_id,
            obj_institution_id=obj_institution_id,
            owner_id=owner_id,
        )

    return _enforce
