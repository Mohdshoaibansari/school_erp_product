"""C-06 Relationship Management — ContactRole routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.authz.dependencies import require_permission
from kernel.relationship.dependencies import get_contact_role_service
from kernel.relationship.services.contact_role_service import ContactRoleService
from kernel.relationship.schemas.dtos import ContactRoleDTO

router = APIRouter(prefix="/api/v1/contact-roles", tags=["contact-roles"])


@router.get("", response_model=list[ContactRoleDTO], summary="List contact roles")
def list_contact_roles(
    _authz: None = Depends(require_permission("contact_role", "read")),
    svc: ContactRoleService = Depends(get_contact_role_service),
) -> list[ContactRoleDTO]:
    """List all ContactRoles."""
    roles = svc.list_all()
    return [ContactRoleDTO.model_validate(r) for r in roles]


@router.get("/compatible/{type_id}", response_model=list[ContactRoleDTO], summary="List compatible roles")
def list_compatible_roles(
    type_id: uuid.UUID,
    _authz: None = Depends(require_permission("contact_role", "read")),
    svc: ContactRoleService = Depends(get_contact_role_service),
) -> list[ContactRoleDTO]:
    """List ContactRoles compatible with a RelationshipType."""
    roles = svc.list_compatible_roles(type_id)
    return [ContactRoleDTO.model_validate(r) for r in roles]
