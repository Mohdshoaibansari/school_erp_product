"""Fees module — Payment routes (D9, D11, D13)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from business.fees.dependencies import get_fees_service
from business.fees.services.service import FeesService
from business.fees.services.dtos import PaymentCreateDTO, PaymentDTO

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentDTO, status_code=status.HTTP_201_CREATED)
def record_payment(
    dto: PaymentCreateDTO,
    _authz: None = Depends(require_permission("payment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> PaymentDTO:
    try:
        return svc.record_payment(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[PaymentDTO])
def list_payments(
    fee_assignment_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    _authz: None = Depends(require_permission("payment", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: FeesService = Depends(get_fees_service),
) -> list[PaymentDTO]:
    try:
        return svc.list_payments(ctx, fee_assignment_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
