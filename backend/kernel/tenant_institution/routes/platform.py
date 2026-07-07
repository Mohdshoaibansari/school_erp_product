"""Platform-scoped router — Platform-Owner-only endpoints (D11, Q5, 7.3, 7.5, 7.7).

Mounts under ``/api/v1/platform/``. Only Platform Owners can access these
endpoints per D11.

Includes:
- 7.3: Client CRUD + identity-update + lifecycle transitions
- 7.5: InstitutionType management
- 7.7: Ownership-transfer request/approval
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, require_platform_owner
from kernel.tenant_institution.dependencies import get_tenant_institution_service
from kernel.tenant_institution.services import (
    TenantInstitutionService,
    ClientCreateDTO,
    ClientDTO,
    ClientUpdateDTO,
    InstitutionTypeCreateDTO,
    InstitutionTypeDTO,
    InstitutionTypeUpdateDTO,
    LifecycleTransitionDTO,
    OwnershipTransferApproveDTO,
    OwnershipTransferEventDTO,
    OwnershipTransferRequestDTO,
    ApprovalDTO,
)

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


# ============================================================
# 7.3 — Client CRUD + identity-update + lifecycle transitions
# ============================================================

@router.post("/clients", response_model=ClientDTO, status_code=status.HTTP_201_CREATED)
def create_client(
    dto: ClientCreateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> ClientDTO:
    """Create a new Client (Platform-Owner-only, D11)."""
    try:
        return svc.create_client(ctx, dto)
    except ValueError as e:
        err = str(e)
        if "reserved" in err.lower():
            raise HTTPException(status_code=400, detail={"error": "slug_reserved", "message": err})
        # Slug collision → 409 "taken" with NO suggestions (Q9, AC-13)
        if "taken" in err.lower() or "unique" in err.lower() or "duplicate" in err.lower():
            raise HTTPException(
                status_code=409,
                detail={"error": "slug_taken", "slug": dto.slug},
            )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clients", response_model=list[ClientDTO])
def list_clients(
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> list[ClientDTO]:
    """List all Clients (Platform-Owner-only, D11)."""
    return svc.list_clients(ctx)


@router.get("/clients/{client_id}", response_model=ClientDTO)
def get_client(
    client_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> ClientDTO:
    """Get a Client by ID (Platform-Owner-only, D11)."""
    result = svc.get_client(ctx, client_id)
    if not result:
        raise HTTPException(status_code=404, detail="Client not found")
    return result


@router.patch("/clients/{client_id}", response_model=ClientDTO)
def update_client(
    client_id: uuid.UUID,
    dto: ClientUpdateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> ClientDTO:
    """Update Client identity (slug immutable, D3/AC-3). Platform-Owner-only (D11)."""
    try:
        return svc.update_client(ctx, client_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Client not found")


@router.post("/clients/{client_id}/transition", response_model=ClientDTO)
def transition_client_lifecycle(
    client_id: uuid.UUID,
    dto: LifecycleTransitionDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> ClientDTO:
    """Transition Client lifecycle (D8 arcs, AC-5). Platform-Owner-only (D11).

    Body must include ``new_state``. Full state-machine + Approval flow is
    sub-phase C (task 8).
    """
    if not dto.new_state:
        raise HTTPException(status_code=400, detail="new_state is required")
    try:
        return svc.transition_client_lifecycle(ctx, client_id, dto.new_state, dto.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 7.5 — InstitutionType management (Platform-Owner-only, D11)
# ============================================================

@router.post("/institution-types", response_model=InstitutionTypeDTO, status_code=status.HTTP_201_CREATED)
def create_institution_type(
    dto: InstitutionTypeCreateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionTypeDTO:
    """Create an InstitutionType (D7, AC-20). Platform-Owner-only (D11)."""
    try:
        return svc.create_institution_type(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/institution-types", response_model=list[InstitutionTypeDTO])
def list_institution_types(
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> list[InstitutionTypeDTO]:
    """List all InstitutionTypes (D7). Platform-Owner-only (D11)."""
    return svc.list_institution_types(ctx)


@router.get("/institution-types/{itype_id}", response_model=InstitutionTypeDTO)
def get_institution_type(
    itype_id: uuid.UUID,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionTypeDTO:
    """Get an InstitutionType by ID (D7). Platform-Owner-only (D11)."""
    result = svc.get_institution_type(ctx, itype_id)
    if not result:
        raise HTTPException(status_code=404, detail="InstitutionType not found")
    return result


@router.patch("/institution-types/{itype_id}", response_model=InstitutionTypeDTO)
def update_institution_type(
    itype_id: uuid.UUID,
    dto: InstitutionTypeUpdateDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionTypeDTO:
    """Update InstitutionType template (D7, AC-16, AC-20). Platform-Owner-only (D11)."""
    try:
        return svc.update_institution_type_template(ctx, itype_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="InstitutionType not found")


# ============================================================
# 7.7 — Ownership-transfer request/approval (D12, AC-11, AC-19)
# ============================================================

@router.post("/ownership-transfers", response_model=ApprovalDTO, status_code=status.HTTP_201_CREATED)
def request_ownership_transfer(
    dto: OwnershipTransferRequestDTO,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> ApprovalDTO:
    """Request an ownership transfer (D12 step 1, AC-19).

    Creates a pending Approval (Q3). Platform-Owner-only (D11).
    Full approval flow + consent is sub-phase C (task 8.4).
    """
    try:
        return svc.request_ownership_transfer(
            ctx, dto.institution_id, dto.to_client_id, dto.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ownership-transfers/{approval_id}/approve", response_model=OwnershipTransferEventDTO)
def approve_ownership_transfer(
    approval_id: uuid.UUID,
    dto: OwnershipTransferApproveDTO,
    to_client_id: uuid.UUID = None,
    ctx: TenantContext = Depends(require_platform_owner),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OwnershipTransferEventDTO:
    """Approve and execute an ownership transfer (D12, AC-11).

    Accepts ``to_client_id`` as a query parameter. Task 11 (Apply-C) will add
    a proper transfer-request record that stores the target client.

    Executes in a single transaction (AC-11). C-11 audit emission deferred to
    Apply-D (task 13.4). C-05/C-02 downstream coordination deferred (boundary).
    Platform-Owner-only (D11).
    """
    if not to_client_id:
        raise HTTPException(status_code=400, detail="to_client_id query parameter is required")

    try:
        # Get the institution_id and from_client_id from the Approval context
        from kernel.tenant_institution.dependencies import get_db_session_factory
        from kernel.tenant_institution.repos import ApprovalRepository
        from kernel.tenant_institution.models import Institution
        from sqlalchemy import select

        sf = get_db_session_factory()
        with sf() as session:
            approval_repo = ApprovalRepository()
            approval = approval_repo.get(session, ctx, approval_id)
            if not approval:
                raise HTTPException(status_code=404, detail="Approval not found")
            if approval.status != "pending":
                raise HTTPException(status_code=400, detail="Approval is not pending")
            institution_id = approval.context_id
            if not institution_id:
                raise HTTPException(status_code=400, detail="Approval has no context_id")

            stmt = select(Institution).where(Institution.id == institution_id)
            inst = session.execute(stmt).scalars().first()
            if not inst:
                raise HTTPException(status_code=404, detail="Institution not found")
            from_client_id = inst.client_id

        return svc.approve_ownership_transfer(
            ctx, approval_id, institution_id, from_client_id, to_client_id,
            dto.consent_source, dto.consent_dest, dto.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
