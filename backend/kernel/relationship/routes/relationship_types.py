"""C-06 Relationship Management — RelationshipType routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.relationship.dependencies import get_relationship_type_service
from kernel.relationship.services.relationship_type_service import RelationshipTypeService
from kernel.relationship.schemas.dtos import RelationshipTypeCreateDTO, RelationshipTypeDTO

router = APIRouter(prefix="/api/v1/relationship-types", tags=["relationship-types"])


@router.post("", response_model=RelationshipTypeDTO, status_code=status.HTTP_201_CREATED, summary="Create relationship type")
def create_relationship_type(
    dto: RelationshipTypeCreateDTO,
    _authz: None = Depends(require_permission("relationship_type", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: RelationshipTypeService = Depends(get_relationship_type_service),
) -> RelationshipTypeDTO:
    """Create a RelationshipType. For non-symmetric types, auto-generates the inverse."""
    try:
        rt = svc.create_relationship_type(
            client_id=ctx.client_id,
            code=dto.code,
            name=dto.name,
            is_symmetric=dto.is_symmetric,
        )
        return RelationshipTypeDTO.model_validate(rt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[RelationshipTypeDTO], summary="List relationship types")
def list_relationship_types(
    _authz: None = Depends(require_permission("relationship_type", "read")),
    svc: RelationshipTypeService = Depends(get_relationship_type_service),
) -> list[RelationshipTypeDTO]:
    """List all RelationshipTypes."""
    types = svc.list_all()
    return [RelationshipTypeDTO.model_validate(rt) for rt in types]
