"""Fees module — FeeAssignment routes (D9, D13)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from business.fees.dependencies import get_fees_service
from business.fees.services.service import FeesService
from business.fees.services.dtos import (
    FeeAssignmentCreateDTO, FeeAssignmentDTO, FeeAssignmentUpdateDTO, WaiveDTO,
)

router = APIRouter(prefix="/api/v1/fee-assignments", tags=["fee-assignments"])


@router.post("", response_model=list[FeeAssignmentDTO], status_code=status.HTTP_201_CREATED)
def create_fee_assignments(
    dto: FeeAssignmentCreateDTO,
    _authz: None = Depends(require_permission("fee_assignment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> list[FeeAssignmentDTO]:
    try:
        return svc.create_fee_assignments(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[FeeAssignmentDTO])
def list_fee_assignments(
    user_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    overdue: bool = False,
    _authz: None = Depends(require_permission("fee_assignment", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> list[FeeAssignmentDTO]:
    try:
        return svc.list_fee_assignments(ctx, user_id, status_filter, overdue)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{assignment_id}", response_model=FeeAssignmentDTO)
def get_fee_assignment(
    assignment_id: uuid.UUID,
    _authz: None = Depends(require_permission("fee_assignment", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeAssignmentDTO:
    result = svc.get_fee_assignment(ctx, assignment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fee assignment not found")
    return result


@router.patch("/{assignment_id}", response_model=FeeAssignmentDTO)
def update_fee_assignment(
    assignment_id: uuid.UUID,
    dto: FeeAssignmentUpdateDTO,
    _authz: None = Depends(require_permission("fee_assignment", "update")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeAssignmentDTO:
    try:
        return svc.update_fee_assignment(ctx, assignment_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{assignment_id}/waive", response_model=FeeAssignmentDTO)
def waive_fee_assignment(
    assignment_id: uuid.UUID,
    dto: WaiveDTO,
    _authz: None = Depends(require_permission("fee_assignment", "waive")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> FeeAssignmentDTO:
    try:
        return svc.waive_fee_assignment(ctx, assignment_id, dto.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
