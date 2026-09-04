"""C-06 Relationship Management — ContactRoleAssignment routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.relationship.dependencies import get_contact_role_assignment_service
from kernel.relationship.services.contact_role_assignment_service import ContactRoleAssignmentService
from kernel.relationship.schemas.dtos import (
    ContactRoleAssignmentCreateDTO,
    ContactRoleAssignmentUpdateDTO,
    ContactRoleAssignmentDTO,
)

router = APIRouter(tags=["contact-role-assignments"])


@router.post(
    "/api/v1/relationships/{relationship_id}/contact-roles",
    response_model=ContactRoleAssignmentDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add contact role to relationship",
)
def add_contact_role(
    relationship_id: uuid.UUID,
    dto: ContactRoleAssignmentCreateDTO,
    _authz: None = Depends(require_permission("contact_role_assignment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: ContactRoleAssignmentService = Depends(get_contact_role_assignment_service),
) -> ContactRoleAssignmentDTO:
    """Add a ContactRole to a Relationship."""
    try:
        cra = svc.add_role(
            client_id=ctx.client_id,
            relationship_id=relationship_id,
            contact_role_id=dto.contact_role_id,
            valid_from=dto.valid_from,
            valid_to=dto.valid_to,
        )
        return ContactRoleAssignmentDTO.model_validate(cra)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/api/v1/relationships/{relationship_id}/contact-roles",
    response_model=list[ContactRoleAssignmentDTO],
    summary="List contact roles for relationship",
)
def list_contact_roles(
    relationship_id: uuid.UUID,
    effective_date: date | None = Query(None, description="Effective date for filtering"),
    _authz: None = Depends(require_permission("contact_role_assignment", "read")),
    svc: ContactRoleAssignmentService = Depends(get_contact_role_assignment_service),
) -> list[ContactRoleAssignmentDTO]:
    """List ContactRoleAssignments for a Relationship."""
    cras = svc.list_by_relationship(relationship_id, effective_date)
    return [ContactRoleAssignmentDTO.model_validate(c) for c in cras]


@router.patch(
    "/api/v1/contact-role-assignments/{assignment_id}",
    response_model=ContactRoleAssignmentDTO,
    summary="Update contact role period",
)
def update_contact_role(
    assignment_id: uuid.UUID,
    dto: ContactRoleAssignmentUpdateDTO,
    _authz: None = Depends(require_permission("contact_role_assignment", "update")),
    svc: ContactRoleAssignmentService = Depends(get_contact_role_assignment_service),
) -> ContactRoleAssignmentDTO:
    """Update a ContactRoleAssignment period."""
    try:
        cra = svc.update_role_period(
            cra_id=assignment_id,
            valid_from=dto.valid_from,
            valid_to=dto.valid_to,
        )
        return ContactRoleAssignmentDTO.model_validate(cra)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/api/v1/contact-role-assignments/{assignment_id}/end",
    response_model=ContactRoleAssignmentDTO,
    summary="End contact role",
)
def end_contact_role(
    assignment_id: uuid.UUID,
    end_date: date,
    _authz: None = Depends(require_permission("contact_role_assignment", "end")),
    svc: ContactRoleAssignmentService = Depends(get_contact_role_assignment_service),
) -> ContactRoleAssignmentDTO:
    """End a ContactRoleAssignment by setting valid_to."""
    try:
        cra = svc.end_role(assignment_id, end_date)
        return ContactRoleAssignmentDTO.model_validate(cra)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
