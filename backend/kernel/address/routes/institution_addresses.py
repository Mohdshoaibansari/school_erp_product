"""C-13 Address Management — Institution address routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import (
    get_address_assignment_service,
    get_address_service,
    get_address_type_repo,
    get_entity_type_service,
)
from kernel.address.repos import AddressTypeRepo, EntityTypeRepo
from kernel.address.schemas.dtos import AddressDTO, EntityAddressCreateDTO
from kernel.address.services import AddressAssignmentService, AddressService
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/api/v1/institutions/{institution_id}/addresses", tags=["institution-addresses"])


def _get_entity_type_id(code: str, repo: EntityTypeRepo) -> uuid.UUID:
    """Resolve EntityType by immutable code; no random UUID."""
    et = repo.get_by_code(code)
    if not et:
        raise HTTPException(status_code=500, detail=f"ENTITY_TYPE_NOT_FOUND: {code} not registered")
    return et.id


def _get_address_type_id(code: str, repo: AddressTypeRepo, entity_type_id: uuid.UUID) -> uuid.UUID:
    """Resolve AddressType by code and validate compatibility with EntityType."""
    at = repo.get_by_code(code)
    if not at:
        raise HTTPException(status_code=400, detail=f"ADDRESS_TYPE_NOT_FOUND: {code} not registered")
    compatible_ids = repo.get_compatible_address_types(entity_type_id)
    if at.id not in compatible_ids:
        raise HTTPException(
            status_code=400, detail="ADDRESS_TYPE_NOT_COMPATIBLE: AddressType not compatible with EntityType"
        )
    return at.id


@router.get("", response_model=list[AddressDTO], summary="List institution addresses")
def list_institution_addresses(
    institution_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "read")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
    entity_type_repo: EntityTypeRepo = Depends(get_entity_type_service),
) -> list[AddressDTO]:
    entity_type_id = _get_entity_type_id("INSTITUTION", entity_type_repo)
    assignments = aa_svc.list_by_entity(
        entity_type_id=entity_type_id,
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
    dto: EntityAddressCreateDTO,
    _authz: None = Depends(require_permission("address", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
    entity_type_repo: EntityTypeRepo = Depends(get_entity_type_service),
    address_type_repo: AddressTypeRepo = Depends(get_address_type_repo),
) -> AddressDTO:
    try:
        entity_type_id = _get_entity_type_id("INSTITUTION", entity_type_repo)
        address_type_id = _get_address_type_id(dto.address_type_code, address_type_repo, entity_type_id)

        addr = svc.create_address(**dto.model_dump(exclude={"address_type_code"}))

        aa_svc.create_assignment(
            entity_type_id=entity_type_id,
            entity_id=institution_id,
            address_id=addr.id,
            address_type_id=address_type_id,
            valid_from=date.today(),
        )

        return AddressDTO.model_validate(addr)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
