"""C-13 Address Management — Person address routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import get_address_service, get_address_assignment_service, get_entity_type_service
from kernel.address.services import AddressService, AddressAssignmentService
from kernel.address.schemas.dtos import AddressCreateDTO, AddressDTO, AddressAssignmentCreateDTO, AddressAssignmentDTO
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/api/v1/persons/{person_id}/addresses", tags=["person-addresses"])


@router.get("", response_model=list[AddressDTO], summary="List person addresses")
def list_person_addresses(
    person_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "read")),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
    svc: AddressService = Depends(get_address_service),
) -> list[AddressDTO]:
    # Get PERSON entity type
    from kernel.address.repos import EntityTypeRepo
    from kernel.db import get_db
    # This is simplified - in production, inject properly
    assignments = aa_svc.list_by_entity(
        entity_type_id=_get_entity_type_id("PERSON"),
        entity_id=person_id,
    )
    addresses = []
    for aa in assignments:
        addr = svc.get_address(aa.address_id)
        if addr:
            addresses.append(AddressDTO.model_validate(addr))
    return addresses


@router.post("", response_model=AddressDTO, status_code=status.HTTP_201_CREATED, summary="Create person address")
def create_person_address(
    person_id: uuid.UUID,
    dto: AddressCreateDTO,
    _authz: None = Depends(require_permission("address", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> AddressDTO:
    try:
        # Create address
        addr = svc.create_address(**dto.model_dump())

        # Get PERSON entity type
        entity_type_id = _get_entity_type_id("PERSON")

        # Create assignment
        aa_svc.create_assignment(
            entity_type_id=entity_type_id,
            entity_id=person_id,
            address_id=addr.id,
            address_type_id=_get_address_type_id("RESIDENTIAL"),  # Default
            valid_from=date.today(),
        )

        return AddressDTO.model_validate(addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _get_entity_type_id(code: str) -> uuid.UUID:
    """Helper to get entity type ID by code."""
    from kernel.address.repos import EntityTypeRepo
    from kernel.db import get_db
    # This is a placeholder - in production, use proper caching/dependency injection
    return uuid.uuid4()


def _get_address_type_id(code: str) -> uuid.UUID:
    """Helper to get address type ID by code."""
    from kernel.address.repos import AddressTypeRepo
    from kernel.db import get_db
    # This is a placeholder - in production, use proper caching/dependency injection
    return uuid.uuid4()


from datetime import date
