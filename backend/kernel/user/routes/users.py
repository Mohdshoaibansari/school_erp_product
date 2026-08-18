"""C-02 User CRUD + lifecycle routes (tasks 9.1, 9.2, T-22).

Endpoints for creating, reading, updating users and transitioning lifecycle.
user_category_id filter removed (T-22, D6a).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission, check_permission, get_enforcer
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import UserService
from kernel.user.services.dtos import (
    UserCreateDTO, UserDTO, UserCreateResponseDTO, UserUpdateDTO, LifecycleTransitionDTO,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ============================================================
# 9.1 — User CRUD endpoints
# ============================================================

@router.post("", response_model=UserCreateResponseDTO, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(
    dto: UserCreateDTO,
    _authz: None = Depends(require_permission("user", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: UserService = Depends(get_identity_user_service),
) -> UserCreateResponseDTO:
    """Create a new User. Returns user + invite_url (D1, D3)."""
    try:
        return await svc.create_user(ctx, dto)
    except ValueError as e:
        err = str(e)
        if "email" in err.lower() and "taken" in err.lower():
            raise HTTPException(status_code=409, detail={"error": "email_taken", "email": dto.email})
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[UserDTO], summary="List users")
def list_users(
    lifecycle_status: str | None = None,
    _authz: None = Depends(require_permission("user", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: UserService = Depends(get_identity_user_service),
) -> list[UserDTO]:
    """List Users, optionally filtered by lifecycle_status.

    D21: Platform owner sees all users across all clients (no tenant filter).
    user_category_id filter removed (T-22, D6a).
    """
    filters = {}
    if lifecycle_status is not None:
        filters["lifecycle_status"] = lifecycle_status
    return svc.list_users(ctx, **filters)


@router.get("/{user_id}", response_model=UserDTO, summary="Get user")
def get_user(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Get a User by ID."""
    result = svc.get_user(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user", "read",
        obj_client_id=result.client_id,
        obj_institution_id=result.institution_id)
    return result


@router.patch("/{user_id}", response_model=UserDTO, summary="Update user")
async def update_user(
    user_id: uuid.UUID,
    dto: UserUpdateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Update User identity fields (email immutable)."""
    existing = svc.get_user(ctx, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user", "update",
        obj_client_id=existing.client_id,
        obj_institution_id=existing.institution_id)
    try:
        return await svc.update_user(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")


# ============================================================
# 9.2 — User lifecycle endpoints
# ============================================================

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> None:
    """Delete a User and all related data (role_assignments, identifiers, Supabase Auth user)."""
    existing = svc.get_user(ctx, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user", "delete",
        obj_client_id=existing.client_id,
        obj_institution_id=existing.institution_id)
    try:
        await svc.delete_user(ctx, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/{user_id}/transition", response_model=UserDTO, summary="Transition user lifecycle")
async def transition_user_lifecycle(
    user_id: uuid.UUID,
    dto: LifecycleTransitionDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Transition User lifecycle (Decision 8, AC-10, AC-11)."""
    if not dto.new_state:
        raise HTTPException(status_code=400, detail="new_state is required")
    existing = svc.get_user(ctx, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user", "suspend",
        obj_client_id=existing.client_id,
        obj_institution_id=existing.institution_id)
    try:
        return await svc.transition_lifecycle(ctx, user_id, dto.new_state, dto.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
