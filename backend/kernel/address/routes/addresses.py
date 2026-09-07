"""C-13 Address Management — Address routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import get_address_service, get_address_assignment_service
from kernel.address.services import AddressService, AddressAssignmentService
from kernel.address.schemas.dtos import AddressCreateDTO, AddressUpdateDTO, AddressDTO, AddressAssignmentCreateDTO, AddressAssignmentDTO
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/api/v1/addresses", tags=["addresses"])


@router.get("/{address_id}", response_model=AddressDTO, summary="Get address")
def get_address(
    address_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "read")),
    svc: AddressService = Depends(get_address_service),
) -> AddressDTO:
    addr = svc.get_address(address_id)
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    return AddressDTO.model_validate(addr)


@router.patch("/{address_id}", response_model=AddressDTO, summary="Update address")
def update_address(
    address_id: uuid.UUID,
    dto: AddressUpdateDTO,
    _authz: None = Depends(require_permission("address", "update")),
    svc: AddressService = Depends(get_address_service),
) -> AddressDTO:
    try:
        addr = svc.update_address(address_id, **dto.model_dump(exclude_unset=True))
        return AddressDTO.model_validate(addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete address")
def delete_address(
    address_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "delete")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> None:
    addr = svc.get_address(address_id)
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    svc.delete_address(addr)


@router.post("/{address_id}/correct", response_model=AddressDTO, summary="Correct address")
def correct_address(
    address_id: uuid.UUID,
    dto: AddressUpdateDTO,
    _authz: None = Depends(require_permission("address", "correct")),
    svc: AddressService = Depends(get_address_service),
) -> AddressDTO:
    try:
        addr = svc.correct_address(address_id, **dto.model_dump(exclude_unset=True))
        return AddressDTO.model_validate(addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
