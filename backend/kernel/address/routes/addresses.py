"""C-13 Address Management — Address routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from kernel.address.dependencies import get_address_service, get_address_assignment_service
from kernel.address.services import AddressService, AddressAssignmentService
from kernel.address.schemas.dtos import AddressCreateDTO, AddressUpdateDTO, AddressDTO, AddressAssignmentCreateDTO, AddressAssignmentDTO
from kernel.authz.dependencies import require_permission
from kernel.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/api/v1/addresses", tags=["addresses"])


class AddressReplaceDTO(BaseModel):
    """Body for atomic replacement — new address data + valid_from."""

    address_line_1: str = Field(..., max_length=500)
    address_line_2: str | None = Field(None, max_length=500)
    locality: str | None = Field(None, max_length=100)
    landmark: str | None = Field(None, max_length=100)
    postal_code: str = Field(..., max_length=20)
    city_id: uuid.UUID
    state_id: uuid.UUID
    country_id: uuid.UUID
    valid_from: date


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


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete address (atomic assignment+address)")
def delete_address(
    address_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "delete")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> None:
    """G-10: Delete via assignment ownership, atomically delete assignment + owned Address.

    Route is DELETE /addresses/{address_id} for backwards-compat, but internally
    resolves the AddressAssignment by address_id and deletes both in one transaction.
    No orphan Address remains; rollback on failure.
    """
    addr = svc.get_address(address_id)
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    # G-10 atomic path: assignment + address in one transaction
    try:
        aa_svc.delete_by_address_id(address_id)
    except ValueError as e:
        msg = str(e)
        if "ADDRESS_ASSIGNMENT_NOT_FOUND" in msg:
            # No assignment — treat as orphan guard: if assigned check failed, try direct delete
            # but AddressService.delete_address will reject if still assigned, so this path
            # is for legacy orphans only.
            try:
                svc.delete_address(addr)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            return
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{address_id}/correct", response_model=AddressDTO, summary="Correct address")
def correct_address(
    address_id: uuid.UUID,
    dto: AddressUpdateDTO,
    _authz: None = Depends(require_permission("address", "correct")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AddressService = Depends(get_address_service),
) -> AddressDTO:
    try:
        addr = svc.correct_address(
            address_id,
            actor=ctx.user_id,
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            **dto.model_dump(exclude_unset=True),
        )
        return AddressDTO.model_validate(addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{address_id}/replace", response_model=AddressDTO, summary="Replace/move address atomically (G-09)")
def replace_address(
    address_id: uuid.UUID,
    dto: AddressReplaceDTO,
    _authz: None = Depends(require_permission("address", "update")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> AddressDTO:
    """G-09: End old assignment, create new Address row, create new assignment in one transaction.

    Old Address stays historical. Never reuse Address rows. Rollback on failure.
    Derives entity_type_id/entity_id/address_type_id from current assignment of address_id.
    """
    # Resolve current assignment to get entity slot
    current = aa_svc.get_by_address_id(address_id)
    if not current:
        raise HTTPException(status_code=404, detail="AddressAssignment not found for address")
    new_address_data = dto.model_dump(exclude={"valid_from"})
    try:
        _new_aa, new_addr = svc.replace_address(
            entity_type_id=current.entity_type_id,
            entity_id=current.entity_id,
            address_type_id=current.address_type_id,
            new_address_data=new_address_data,
            valid_from=dto.valid_from,
        )
        return AddressDTO.model_validate(new_addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# G-10 complement: DELETE via assignment id (preferred explicit path)
# ------------------------------------------------------------------
assignment_router = APIRouter(prefix="/api/v1/address-assignments", tags=["address-assignments"])


@assignment_router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete address-assignment atomically (G-10)")
def delete_assignment(
    assignment_id: uuid.UUID,
    _authz: None = Depends(require_permission("address", "delete")),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> None:
    """G-10: Delete AddressAssignment + owned Address in one transaction."""
    aa = aa_svc.get_assignment(assignment_id)
    if not aa:
        raise HTTPException(status_code=404, detail="AddressAssignment not found")
    try:
        aa_svc.delete_assignment_and_address(assignment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@assignment_router.post("/{assignment_id}/replace", response_model=AddressDTO, summary="Replace/move via assignment id (G-09)")
def replace_via_assignment(
    assignment_id: uuid.UUID,
    dto: AddressReplaceDTO,
    _authz: None = Depends(require_permission("address", "update")),
    svc: AddressService = Depends(get_address_service),
    aa_svc: AddressAssignmentService = Depends(get_address_assignment_service),
) -> AddressDTO:
    current = aa_svc.get_assignment(assignment_id)
    if not current:
        raise HTTPException(status_code=404, detail="AddressAssignment not found")
    new_address_data = dto.model_dump(exclude={"valid_from"})
    try:
        _new_aa, new_addr = svc.replace_address(
            entity_type_id=current.entity_type_id,
            entity_id=current.entity_id,
            address_type_id=current.address_type_id,
            new_address_data=new_address_data,
            valid_from=dto.valid_from,
        )
        return AddressDTO.model_validate(new_addr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
