"""C-02 UserProfile routes (task 9.3).

Endpoints for creating, reading, updating user profiles.
D13: Self-service — any user can manage own profile. Admins can manage any.
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
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Create a UserProfile. Self-creation (owner_id) bypasses permission check.
    Admin creating on behalf of others uses user_profile.create permission."""
    check_permission(ctx, enforcer, "user_profile", "create", owner_id=user_id)
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
    """Get a UserProfile by user_id. Self-read (owner_id) bypasses permission check."""
    result = svc.get_profile(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    check_permission(ctx, enforcer, "user_profile", "read", owner_id=user_id)
    return result


@router.patch("", response_model=UserProfileDTO, summary="Update user profile")
def update_profile(
    user_id: uuid.UUID,
    dto: UserProfileUpdateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    enforcer: Any = Depends(get_enforcer),
    svc: UserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Update a UserProfile. Self-update (owner_id) bypasses permission check."""
    check_permission(ctx, enforcer, "user_profile", "update", owner_id=user_id)
    try:
        return svc.update_profile(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
