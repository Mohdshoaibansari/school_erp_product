"""C-02 UserProfile routes (task 9.3).

Endpoints for creating, reading, updating user profiles.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import IdentityUserService
from kernel.user.services.dtos import UserProfileCreateDTO, UserProfileDTO, UserProfileUpdateDTO

router = APIRouter(prefix="/api/v1/users/{user_id}/profile", tags=["profiles"])


@router.post("", response_model=UserProfileDTO, status_code=status.HTTP_201_CREATED)
def create_profile(
    user_id: uuid.UUID,
    dto: UserProfileCreateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Create a UserProfile for a User."""
    try:
        return svc.create_profile(ctx, user_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=UserProfileDTO)
def get_profile(
    user_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Get a UserProfile by user_id."""
    result = svc.get_profile(ctx, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.patch("", response_model=UserProfileDTO)
def update_profile(
    user_id: uuid.UUID,
    dto: UserProfileUpdateDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> UserProfileDTO:
    """Update a UserProfile."""
    try:
        return svc.update_profile(ctx, user_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found")
