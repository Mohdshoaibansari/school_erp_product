"""C-02 RoleAssignment routes (task 9.4).

Endpoints for creating, listing, deleting role assignments.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.user.dependencies import get_identity_user_service
from kernel.user.services.service import IdentityUserService
from kernel.user.services.dtos import RoleAssignmentCreateDTO, RoleAssignmentDTO

router = APIRouter(prefix="/api/v1/users/{user_id}/roles", tags=["roles"])


@router.post("", response_model=RoleAssignmentDTO, status_code=status.HTTP_201_CREATED)
def create_role_assignment(
    user_id: uuid.UUID,
    dto: RoleAssignmentCreateDTO,
    _authz: None = Depends(require_permission("role_assignment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> RoleAssignmentDTO:
    """Create a RoleAssignment for a User."""
    try:
        return svc.create_role_assignment(ctx, user_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[RoleAssignmentDTO])
def list_role_assignments(
    user_id: uuid.UUID,
    _authz: None = Depends(require_permission("role_assignment", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> list[RoleAssignmentDTO]:
    """List RoleAssignments for a User."""
    return svc.list_role_assignments(ctx, user_id)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_assignment(
    user_id: uuid.UUID,
    assignment_id: uuid.UUID,
    _authz: None = Depends(require_permission("role_assignment", "delete")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: IdentityUserService = Depends(get_identity_user_service),
) -> None:
    """Delete a RoleAssignment."""
    try:
        svc.delete_role_assignment(ctx, assignment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="RoleAssignment not found")
