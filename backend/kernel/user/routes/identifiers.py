"""C-02 UserIdentifier routes (task 9.5).

Endpoints for creating, listing, deleting user identifiers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import IdentityUserService
from kernel.user.services.dtos import UserIdentifierCreateDTO, UserIdentifierDTO

router = APIRouter(prefix="/api/v1/users/{user_id}/identifiers", tags=["identifiers"])


@router.post("", response_model=UserIdentifierDTO, status_code=status.HTTP_201_CREATED)
def create_identifier(
    user_id: uuid.UUID,
    dto: UserIdentifierCreateDTO,
    _authz: None = Depends(require_permission("user_identifier", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserIdentifierDTO:
    """Create a UserIdentifier for a User."""
    try:
        return svc.create_identifier(ctx, user_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[UserIdentifierDTO])
def list_identifiers(
    user_id: uuid.UUID,
    _authz: None = Depends(require_permission("user_identifier", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> list[UserIdentifierDTO]:
    """List UserIdentifiers for a User."""
    return svc.list_identifiers(ctx, user_id)


@router.delete("/{identifier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_identifier(
    user_id: uuid.UUID,
    identifier_id: uuid.UUID,
    _authz: None = Depends(require_permission("user_identifier", "delete")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> None:
    """Delete a UserIdentifier."""
    try:
        svc.delete_identifier(ctx, identifier_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="UserIdentifier not found")
