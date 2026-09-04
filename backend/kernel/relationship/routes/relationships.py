"""C-06 Relationship Management — Relationship routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.relationship.dependencies import get_relationship_service
from kernel.relationship.services.relationship_service import RelationshipService
from kernel.relationship.schemas.dtos import RelationshipCreateDTO, RelationshipUpdateDTO, RelationshipDTO

router = APIRouter(prefix="/api/v1/people/{person_id}/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipDTO, status_code=status.HTTP_201_CREATED, summary="Create relationship")
def create_relationship(
    person_id: uuid.UUID,
    dto: RelationshipCreateDTO,
    _authz: None = Depends(require_permission("relationship", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: RelationshipService = Depends(get_relationship_service),
) -> RelationshipDTO:
    """Create a Relationship between two Persons."""
    try:
        rel = svc.create_relationship(
            client_id=ctx.client_id,
            person_a_id=dto.person_a_id,
            person_b_id=dto.person_b_id,
            relationship_type_id=dto.relationship_type_id,
            valid_from=dto.valid_from,
            valid_to=dto.valid_to,
        )
        return RelationshipDTO.model_validate(rel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[RelationshipDTO], summary="List relationships")
def list_relationships(
    person_id: uuid.UUID,
    effective_date: date | None = Query(None, description="Effective date for filtering"),
    relationship_type_id: uuid.UUID | None = Query(None, description="Filter by relationship type"),
    _authz: None = Depends(require_permission("relationship", "read")),
    svc: RelationshipService = Depends(get_relationship_service),
) -> list[RelationshipDTO]:
    """List Relationships for a Person."""
    rels = svc.list_by_person(person_id, effective_date, relationship_type_id)
    return [RelationshipDTO.model_validate(r) for r in rels]
