"""C-13 Address Management — AddressType routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.address.dependencies import get_address_type_service
from kernel.address.services import AddressTypeService
from kernel.address.schemas.dtos import AddressTypeDTO, EntityTypeDTO
from kernel.authz.dependencies import require_permission
from kernel.address.repos import EntityTypeRepo, AddressTypeRepo

router = APIRouter(prefix="/api/v1/address-types", tags=["address-types"])


@router.get("", response_model=list[AddressTypeDTO], summary="List address types")
def list_address_types(
    _authz: None = Depends(require_permission("address_type", "read")),
    svc: AddressTypeService = Depends(get_address_type_service),
) -> list[AddressTypeDTO]:
    types = svc.list_types()
    return [AddressTypeDTO.model_validate(t) for t in types]


@router.get("/compatible", response_model=list[AddressTypeDTO], summary="List compatible address types")
def list_compatible_types(
    entity_type_id: uuid.UUID,
    _authz: None = Depends(require_permission("address_type", "read")),
    svc: AddressTypeService = Depends(get_address_type_service),
) -> list[AddressTypeDTO]:
    types = svc.list_compatible_types(entity_type_id)
    return [AddressTypeDTO.model_validate(t) for t in types]
