"""C-02 User CRUD + lifecycle routes (tasks 9.1, 9.2).

Endpoints for creating, reading, updating users and transitioning lifecycle.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import IdentityUserService
from kernel.user.services.dtos import UserCreateDTO, UserDTO, UserUpdateDTO, LifecycleTransitionDTO

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ============================================================
# 9.1 — User CRUD endpoints
# ============================================================

@router.post("", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    dto: UserCreateDTO,
    _authz: None = Depends(require_permission("user", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Create a new User."""
    try:
        return await svc.create_user(ctx, dto)
    except ValueError as e:
        err = str(e)
        if "email" in err.lower() and "taken" in err.lower():
            raise HTTPException(status_code=409, detail={"error": "email_taken", "email": dto.email})
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[UserDTO])
def list_users(
    user_category_id: uuid.UUID | None = None,
    lifecycle_status: str | None = None,
    _authz: None = Depends(require_permission("user", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> list[UserDTO]:
    """List Users, optionally filtered by user_category_id or lifecycle_status."""
    filters = {}
    if user_category_id is not None:
        filters["user_category_id"] = user_category_id
    if lifecycle_status is not None:
        filters["lifecycle_status"] = lifecycle_status
    return svc.list_users(ctx, **filters)


@router.get("/{user_id}", response_model=UserDTO)
def get_user(
    user_id: uuid.UUID,
    _authz: None = Depends(require_permission("user", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Get a User by ID."""
    result = svc.get_user(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.patch("/{user_id}", response_model=UserDTO)
async def update_user(
    user_id: uuid.UUID,
    dto: UserUpdateDTO,
    _authz: None = Depends(require_permission("user", "update")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Update User identity fields (email immutable)."""
    try:
        return await svc.update_user(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")


# ============================================================
# 9.2 — User lifecycle endpoints
# ============================================================

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    _authz: None = Depends(require_permission("user", "delete")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> None:
    """Delete a User and all related data (role_assignments, identifiers, Supabase Auth user)."""
    try:
        svc.delete_user(ctx, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")


# ============================================================
# 9.2 — User lifecycle endpoints
# ============================================================

@router.post("/{user_id}/transition", response_model=UserDTO)
async def transition_user_lifecycle(
    user_id: uuid.UUID,
    dto: LifecycleTransitionDTO,
    _authz: None = Depends(require_permission("user", "suspend")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserDTO:
    """Transition User lifecycle (Decision 8, AC-10, AC-11).

    Body must include ``new_state``. Allowed transitions:
    Invited→Pending, Pending→Active, Active→Suspended, Suspended→Active,
    Active→Archived, Suspended→Archived. Archived is terminal.
    """
    if not dto.new_state:
        raise HTTPException(status_code=400, detail="new_state is required")
    try:
        return await svc.transition_lifecycle(ctx, user_id, dto.new_state, dto.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
