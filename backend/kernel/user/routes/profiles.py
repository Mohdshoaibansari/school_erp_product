"""C-02 UserProfile routes (task 9.3).

Endpoints for creating, reading, updating user profiles.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission, check_permission, get_enforcer
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import UserService
from kernel.user.services.dtos import UserProfileCreateDTO, UserProfileDTO, UserProfileUpdateDTO

router = APIRouter(prefix="/api/v1/users/{user_id}/profile", tags=["profiles"])


@router.post("", response_model=UserProfileDTO, status_code=status.HTTP_201_CREATED, summary="Create user profile")
def create_profile(
    user_id: uuid.UUID,
    dto: UserProfileCreateDTO,
    _authz: None = Depends(require_permission("user_profile", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Create a UserProfile for a User."""
    try:
        return svc.create_profile(ctx, user_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=UserProfileDTO, summary="Get user profile")
def get_profile(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Get a UserProfile by user_id."""
    result = svc.get_profile(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    # ABAC: check via parent user's client/institution
    user = svc.get_user(ctx, user_id)
    check_permission(ctx, enforcer, "user_profile", "read",
        obj_client_id=user.client_id if user else ctx.client_id,
        obj_institution_id=user.institution_id if user else ctx.institution_id)
    return result


@router.patch("", response_model=UserProfileDTO, summary="Update user profile")
def update_profile(
    user_id: uuid.UUID,
    dto: UserProfileUpdateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Update a UserProfile. Users can update their own profile; admins can update any."""
    user = svc.get_user(ctx, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    check_permission(ctx, enforcer, "user_profile", "update",
        obj_client_id=user.client_id,
        obj_institution_id=user.institution_id,
        owner_id=user_id)  # ownership check: self or admin
    try:
        return svc.update_profile(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
