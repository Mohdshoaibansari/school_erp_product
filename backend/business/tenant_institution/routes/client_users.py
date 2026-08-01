"""Client User Bootstrap — PO platform routes (D4, D6).

Nested under /api/v1/platform/clients/{client_id}/users.
PO-only endpoints for Client Director provisioning, listing, lifecycle management,
and revocation. Protected by require_platform_owner.
"""

from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, require_platform_owner
from kernel.user.services.client_user_service import ClientUserService
from kernel.user.services.dtos import (
    ClientUserCreateDTO,
    ClientUserDTO,
    ClientUserUpdateDTO,
    ClientUserTransitionDTO,
)
from kernel.user.dependencies import get_client_user_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_client_id_and_ctx(
    client_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
) -> tuple[uuid.UUID, TenantContext]:
    """Helper: validate PO context and return client_id."""
    return client_id, ctx


@router.post(
    "/api/v1/platform/clients/{client_id}/users",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap Client Director (PO-only)",
)
async def bootstrap_client_director(
    client_id: uuid.UUID,
    dto: ClientUserCreateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
):
    """Bootstrap the first Client Director for a client.

    Creates Supabase Auth user in 'invited' state (no password),
    inserts client_user row with lifecycle_status='invited',
    mints invite JWT, and returns the invite URL for the PO to forward.
    Per D4, D6, D7.
    """
    try:
        result = await svc.bootstrap_invite(ctx, client_id, dto)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/api/v1/platform/clients/{client_id}/users",
    response_model=list[ClientUserDTO],
    summary="List Client Directors in a client (PO-only)",
)
def list_client_users(
    client_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
) -> list[ClientUserDTO]:
    """List all client-leadership users in the given client.
    Returns rows across all lifecycle states. Per D4."""
    return svc.list_in_client(ctx, client_id)


@router.get(
    "/api/v1/platform/clients/{client_id}/users/{user_id}",
    response_model=ClientUserDTO,
    summary="Get a Client Director (PO or own)",
)
def get_client_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
) -> ClientUserDTO:
    """Get a single ClientUser by ID. PO gets any; CD gets own row (filtered by RLS)."""
    result = svc.get_by_id(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="ClientUser not found")
    return result


@router.patch(
    "/api/v1/platform/clients/{client_id}/users/{user_id}",
    response_model=ClientUserDTO,
    summary="Update a Client Director (name, email)",
)
def update_client_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    dto: ClientUserUpdateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
) -> ClientUserDTO:
    """Update a ClientUser's identity fields (name, email).
    CD can update own row (RLS-filtered); PO can update any."""
    try:
        return svc.update_own(ctx, user_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/api/v1/platform/clients/{client_id}/users/{user_id}/transition",
    response_model=ClientUserDTO,
    summary="Transition Client Director lifecycle (PO-only)",
)
def transition_client_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    transition: ClientUserTransitionDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
) -> ClientUserDTO:
    """Transition a CD's lifecycle: suspend, reinstate, archive. PO-only. Per D4, D10."""
    try:
        return svc.transition_lifecycle(ctx, user_id, transition)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/api/v1/platform/clients/{client_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a Client Director (PO-only)",
)
async def revoke_client_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: ClientUserService = Depends(get_client_user_service),
    reason: str | None = None,
):
    """Revoke a CD: archive client_user row + delete Supabase Auth user.
    Per D4, R2 (transactional cleanup to prevent user_tier drift)."""
    try:
        await svc.revoke(ctx, user_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
