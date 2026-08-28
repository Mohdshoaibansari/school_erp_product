"""C-04 Authorization — FastAPI dependencies (D5, D7, D10, D11, D12, D13, D19, D22, D31).

Provides:
- ``get_enforcer()`` — the global Casbin enforcer singleton.
- ``get_authorization_service()`` — the global AuthorizationService singleton.
- ``require_permission(resource, action, ...)`` — async FastAPI dependency for
  authorization checks. Thin adapter over AuthorizationService.
- ``check_permission(ctx, enforcer, resource, action, ...)`` — async callable for
  inline ABAC checks after fetching a resource.

Extended for ABAC (D11):
- Both entry points are now async adapters over AuthorizationService.
- Structured 403 with reason code on denial.
- Platform Owner evaluated through the normal pipeline (bypass removed —
  PO is granted only by configured role_permission rows; effective role
  label derived per D5).
- ``roles[0]`` bug removed — multi-role evaluation via pipeline.
- Hardcoded ``owner_id`` bypass removed — replaced by ``is_self`` attribute (D10).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)

from kernel.tenant_context import TenantContext, get_tenant_context

_enforcer: Any = None
_authorization_service: Any = None


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


def set_authorization_service(service: Any) -> None:
    """Store the global AuthorizationService singleton (called by app factory)."""
    global _authorization_service
    _authorization_service = service


def get_authorization_service() -> Any:
    """Return the global AuthorizationService singleton."""
    return _authorization_service


def _build_request(
    ctx: TenantContext,
    resource: str,
    action: str,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> Any:
    """Build an AuthorizationRequest from TenantContext and explicit object attrs.

    Maps TenantContext → SubjectContext, explicit object attrs → ResourceContext.
    Falls back to ctx values for backward compatibility (AC-12).
    Routes owner_id through ResourceContext.data["owner_id"] (D10).
    """
    from kernel.authz.models.authorization_types import (
        AuthorizationRequest,
        ResourceContext,
        SubjectContext,
    )

    subject = SubjectContext.from_tenant_context(ctx)

    # Build resource data dict — include owner_id for is_self resolution (D10)
    data: dict[str, Any] = {}
    if owner_id is not None:
        data["owner_id"] = str(owner_id)

    resource_ctx = ResourceContext(
        resource_type=resource,
        resource_id=None,
        client_id=obj_client_id if obj_client_id is not None else ctx.client_id,
        institution_id=obj_institution_id if obj_institution_id is not None else ctx.institution_id,
        data=data,
    )

    return AuthorizationRequest(
        subject=subject,
        resource=resource_ctx,
        action=action,
    )


def _to_http_403(decision: Any) -> HTTPException:
    """Convert an AuthorizationDecision to a structured HTTP 403 (D11).

    Exposes the machine-readable reason code, never policy internals.
    """
    return HTTPException(
        status_code=403,
        detail={
            "code": decision.reason.value,
            "message": "Permission denied",
        },
    )


async def check_permission(
    ctx: TenantContext,
    enforcer: Any,
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> None:
    """Check authorization inline (async adapter over AuthorizationService).

    Usage in routes:
        institution = svc.get(institution_id)
        await check_permission(ctx, enforcer, "institution", "read",
            obj_client_id=institution.client_id,
            obj_institution_id=institution.id)

    Raises HTTPException(403) with structured reason code on denial.
    """
    svc = get_authorization_service()
    if svc is None:
        # Fallback to legacy _check_impl if AuthorizationService not wired
        logger.warning("[AUTHZ] AuthorizationService not available, falling back to legacy check")
        _check_impl_legacy(
            ctx, enforcer, resource, action,
            obj_client_id=obj_client_id,
            obj_institution_id=obj_institution_id,
            owner_id=owner_id,
        )
        return

    request = _build_request(ctx, resource, action, obj_client_id, obj_institution_id, owner_id)
    decision = await svc.authorize(request)
    if not decision.allowed:
        raise _to_http_403(decision)


def require_permission(
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
):
    """FastAPI async dependency: enforce authorization via AuthorizationService pipeline.

    Usage:
        @router.post("/institutions")
        async def create(..., _ = Depends(require_permission("institution", "create"))):
            ...

        @router.get("/institutions")
        async def list(..., _ = Depends(require_permission("institution", "read",
                    obj_client_id=ctx.client_id))):
            ...

    Object attributes (obj_client_id, obj_institution_id) are passed explicitly
    by the calling endpoint for ABAC enforcement (D7, D19). When not provided,
    falls back to TenantContext values (backward compatible).

    Returns a dependency closure that reads ``TenantContext`` and the Casbin
    enforcer, then enforces via the AuthorizationService pipeline.

    Raises ``HTTPException(403)`` with structured reason code on denial.
    """

    async def _enforce(
        ctx: TenantContext = Depends(get_tenant_context),
        enforcer: Any = Depends(get_enforcer),
    ):
        svc = get_authorization_service()
        if svc is None:
            # Fallback to legacy _check_impl if AuthorizationService not wired
            logger.warning("[AUTHZ] AuthorizationService not available, falling back to legacy check")
            _check_impl_legacy(
                ctx, enforcer, resource, action,
                obj_client_id=obj_client_id,
                obj_institution_id=obj_institution_id,
                owner_id=owner_id,
            )
            return

        request = _build_request(ctx, resource, action, obj_client_id, obj_institution_id, owner_id)
        decision = await svc.authorize(request)
        if not decision.allowed:
            raise _to_http_403(decision)

    return _enforce


def _check_impl_legacy(
    ctx: TenantContext,
    enforcer: Any,
    resource: str,
    action: str,
    *,
    obj_client_id: uuid.UUID | None = None,
    obj_institution_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> None:
    """Legacy authorization logic — fallback when AuthorizationService is not wired.

    Preserves the original behavior for backward compatibility during migration.
    """
    if enforcer is None:
        logger.error("[AUTHZ] Enforcer not available")
        raise HTTPException(status_code=500, detail="Authorization service not available")

    roles = ctx.roles or []

    # Platform Owner effective role label (D5) — role derivation, NOT a bypass:
    # PO JWTs carry no roles claim; derive the existing "platform_owner" DB role so
    # configured role_permission rows (client.*, config.*) match via Casbin g().
    # Grants still come only from role_permission rows evaluated by the pipeline.
    if ctx.is_platform_owner and "platform_owner" not in roles:
        roles = ["platform_owner"] + roles

    if not roles:
        logger.warning("[AUTHZ] No roles assigned: user=%s resource=%s action=%s", ctx.user_id, resource, action)
        raise HTTPException(status_code=403, detail="Permission denied — no roles assigned")

    # Build Casbin subject from TenantContext — evaluate ALL roles (D7)
    obj = {
        "name": resource,
        "client_id": str(obj_client_id) if obj_client_id is not None
                     else (str(ctx.client_id) if ctx.client_id else ""),
        "institution_id": str(obj_institution_id) if obj_institution_id is not None
                          else (str(ctx.institution_id) if ctx.institution_id else ""),
    }

    # Multi-role evaluation: loop per role (D7)
    for role in roles:
        sub = {
            "role": role,
            "client_id": str(ctx.client_id) if ctx.client_id else "",
            "institution_id": str(ctx.institution_id) if ctx.institution_id else "",
        }
        if enforcer.enforce(sub, obj, action):
            logger.debug("[AUTHZ] Permission granted: user=%s role=%s resource=%s action=%s",
                         ctx.user_id, role, resource, action)
            return

    logger.warning("[AUTHZ] Permission denied: user=%s roles=%s resource=%s action=%s",
                   ctx.user_id, roles, resource, action)
    raise HTTPException(status_code=403, detail="Permission denied")
