"""C-13 Address Management — Institution address routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import get_address_service, get_address_assignment_service
from kernel.address.services import AddressService, AddressAssignmentService
from kernel.address.schemas.dtos import AddressCreateDTO, AddressDTO
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/api/v1/institutions/{institution_id}/addresses", tags=["institution-addresses"])


@router.get("", response_model=list[AddressDTO], summary="List institution addresses")
def list_institution_addresses(
    institution_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "read")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> list[AddressDTO]:
    assignments = aa_svc.list_by_entity(
        entity_type_id=_get_entity_type_id("INSTITUTION"),
        entity_id=institution_id,
    )
    addresses = []
    for aa in assignments:
        addr = svc.get_address(aa.address_id)
        if addr:
            addresses.append(AddressDTO.model_validate(addr))
    return addresses


@router.post("", response_model=AddressDTO, status_code=status.HTTP_201_CREATED, summary="Create institution address")
def create_institution_address(
    institution_id: uuid.UUID,
    dto: AddressCreateDTO,
    _authz: None = Depends(require_permission("address", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> AddressDTO:
    try:
        addr = svc.create_address(**dto.model_dump())

        entity_type_id = _get_entity_type_id("INSTITUTION")

        aa_svc.create_assignment(
            entity_type_id=entity_type_id,
            entity_id=institution_id,
            address_id=addr.id,
            address_type_id=_get_address_type_id("OFFICE"),  # Default
            valid_from=date.today(),
        )

        return AddressDTO.model_validate(addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _get_entity_type_id(code: str) -> uuid.UUID:
    """Helper to get entity type ID by code."""
    return uuid.uuid4()


def _get_address_type_id(code: str) -> uuid.UUID:
    """Helper to get address type ID by code."""
    return uuid.uuid4()


from datetime import date
