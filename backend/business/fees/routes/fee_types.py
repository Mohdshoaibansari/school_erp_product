"""Fees module — FeeType routes (D9)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from business.fees.dependencies import get_fees_service
from business.fees.services.service import FeesService
from business.fees.services.dtos import FeeTypeCreateDTO, FeeTypeDTO, FeeTypeUpdateDTO

router = APIRouter(prefix="/api/v1/fee-types", tags=["fee-types"])


@router.post("", response_model=FeeTypeDTO, status_code=status.HTTP_201_CREATED)
def create_fee_type(
    dto: FeeTypeCreateDTO,
    _authz: None = Depends(require_permission("fee", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeTypeDTO:
    try:
        return svc.create_fee_type(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[FeeTypeDTO])
def list_fee_types(
    institution_id: uuid.UUID | None = None,
    _authz: None = Depends(require_permission("fee", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> list[FeeTypeDTO]:
    return svc.list_fee_types(ctx, institution_id)


@router.get("/{fee_type_id}", response_model=FeeTypeDTO)
def get_fee_type(
    fee_type_id: uuid.UUID,
    _authz: None = Depends(require_permission("fee", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeTypeDTO:
    result = svc.get_fee_type(ctx, fee_type_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fee type not found")
    return result


@router.patch("/{fee_type_id}", response_model=FeeTypeDTO)
def update_fee_type(
    fee_type_id: uuid.UUID,
    dto: FeeTypeUpdateDTO,
    _authz: None = Depends(require_permission("fee", "update")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeTypeDTO:
    try:
        return svc.update_fee_type(ctx, fee_type_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Fee type not found")


@router.delete("/{fee_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fee_type(
    fee_type_id: uuid.UUID,
    _authz: None = Depends(require_permission("fee", "delete")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> None:
    try:
        svc.deactivate_fee_type(ctx, fee_type_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Fee type not found")
