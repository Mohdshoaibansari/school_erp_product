"""Client-portal subdomain router (Q5, 7.4, 7.6).

Mounts under ``/api/v1/`` (subdomain-resolved). The Client is implicit from
the subdomain per D3 — DO NOT accept ``client_slug`` in the path.

Includes:
- 7.4: Institution CRUD + identity-update + lifecycle transitions + go-live
- 7.6: OrgUnit endpoints (create, move, archive, reactivate, reorder)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from business.tenant_institution.dependencies import get_tenant_institution_service
from business.tenant_institution.services import (
    TenantInstitutionService,
    InstitutionCreateDTO,
    InstitutionDTO,
    InstitutionUpdateDTO,
    LifecycleTransitionDTO,
    OrgUnitCreateDTO,
    OrgUnitDTO,
    OrgUnitMoveDTO,
    OrgUnitReorderDTO,
)

router = APIRouter(prefix="/api/v1", tags=["client-portal"])


# ============================================================
# 7.4 — Institution CRUD + identity-update + lifecycle + go-live
# ============================================================

@router.post("/institutions", response_model=InstitutionDTO, status_code=status.HTTP_201_CREATED)
def create_institution(
    dto: InstitutionCreateDTO,
    _authz: None = Depends(require_permission("institution", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionDTO:
    """Create an Institution under the resolved Client (D5, AC-12).

    Client is implicit from the subdomain (D3, Q5). The superseded
    ``POST /api/clients/{slug}/institutions`` form MUST NOT be used.
    """
    if not ctx.client_id:
        raise HTTPException(status_code=400, detail="Client not resolved from subdomain")
    try:
        return svc.create_institution(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/institutions", response_model=list[InstitutionDTO])
def list_institutions(
    cross_institution: bool = False,
    _authz: None = Depends(require_permission("institution", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> list[InstitutionDTO]:
    """List Institutions under the resolved Client (D5, D11).

    ``cross_institution=True`` omits the ``institution_id`` default filter for
    authorized cross-institution roles (Client Director — D11).
    """
    return svc.list_institutions(ctx, cross_institution=cross_institution)


@router.get("/institutions/{institution_id}", response_model=InstitutionDTO)
def get_institution(
    institution_id: uuid.UUID,
    _authz: None = Depends(require_permission("institution", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionDTO:
    """Get an Institution by ID (D5)."""
    result = svc.get_institution(ctx, institution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Institution not found")
    return result


@router.patch("/institutions/{institution_id}", response_model=InstitutionDTO)
def update_institution(
    institution_id: uuid.UUID,
    dto: InstitutionUpdateDTO,
    _authz: None = Depends(require_permission("institution", "update")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionDTO:
    """Update Institution identity (institution_type_id immutable, D7/AC-16)."""
    try:
        return svc.update_institution(ctx, institution_id, dto)
    except ValueError:
        raise HTTPException(status_code=404, detail="Institution not found")


@router.post("/institutions/{institution_id}/transition", response_model=InstitutionDTO)
def transition_institution_lifecycle(
    institution_id: uuid.UUID,
    dto: LifecycleTransitionDTO,
    _authz: None = Depends(require_permission("institution", "transition_lifecycle")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionDTO:
    """Transition Institution lifecycle (D9 arcs, AC-6).

    Body must include ``new_state``. Go-live = Onboarding→Active (D9).
    Full state-machine + Approval flow is sub-phase C (task 8).
    """
    if not dto.new_state:
        raise HTTPException(status_code=400, detail="new_state is required")
    try:
        return svc.transition_institution_lifecycle(ctx, institution_id, dto.new_state, dto.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/institutions/{institution_id}/go-live", response_model=InstitutionDTO)
def go_live_institution(
    institution_id: uuid.UUID,
    dto: LifecycleTransitionDTO,
    _authz: None = Depends(require_permission("institution", "transition_lifecycle")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> InstitutionDTO:
    """Go-live: Onboarding → Active (D9, 7.4).

    Convenience endpoint for the go-live transition. Full Approval flow is
    sub-phase C (task 8.4).
    """
    try:
        return svc.transition_institution_lifecycle(
            ctx, institution_id, "active", dto.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Note: the go-live endpoint passes new_state="active" directly to the service.


# ============================================================
# 7.6 — OrgUnit endpoints (create, move, archive, reactivate, reorder)
# ============================================================

@router.post("/org-units", response_model=OrgUnitDTO, status_code=status.HTTP_201_CREATED)
def create_org_unit(
    dto: OrgUnitCreateDTO,
    _authz: None = Depends(require_permission("org_unit", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OrgUnitDTO:
    """Create an OrgUnit (D6). Client-portal base, Institution/Admin scope (D11)."""
    if not ctx.client_id:
        raise HTTPException(status_code=400, detail="Client not resolved from subdomain")
    try:
        return svc.create_org_unit(ctx, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/org-units", response_model=list[OrgUnitDTO])
def list_org_units(
    institution_id: uuid.UUID,
    cross_institution: bool = False,
    _authz: None = Depends(require_permission("org_unit", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> list[OrgUnitDTO]:
    """List OrgUnits under an institution (D6, D11)."""
    return svc.list_org_units(ctx, institution_id, cross_institution=cross_institution)


@router.get("/org-units/{org_unit_id}/subtree", response_model=list[OrgUnitDTO])
def get_org_unit_subtree(
    org_unit_id: uuid.UUID,
    _authz: None = Depends(require_permission("org_unit", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> list[OrgUnitDTO]:
    """Get the full subtree of an OrgUnit using a recursive CTE (D6)."""
    return svc.get_org_unit_subtree(ctx, org_unit_id)


@router.post("/org-units/{org_unit_id}/move", response_model=OrgUnitDTO)
def move_org_unit(
    org_unit_id: uuid.UUID,
    dto: OrgUnitMoveDTO,
    _authz: None = Depends(require_permission("org_unit", "move")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OrgUnitDTO:
    """Move an OrgUnit (D6, AC-9 — cycle-prevented, subtree moves).

    C-11 audit emission for the move deferred to Apply-D (task 13.3).
    Move currently persists without audit; AC-10 full coverage deferred.
    """
    try:
        return svc.move_org_unit(ctx, org_unit_id, dto.new_parent_id)
    except ValueError as e:
        if "cycle" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/org-units/{org_unit_id}/archive", response_model=OrgUnitDTO)
def archive_org_unit(
    org_unit_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OrgUnitDTO:
    """Archive an OrgUnit (D6, AC-8 — archive-only, no hard delete)."""
    try:
        return svc.archive_org_unit(ctx, org_unit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="OrgUnit not found")


@router.post("/org-units/{org_unit_id}/reactivate", response_model=OrgUnitDTO)
def reactivate_org_unit(
    org_unit_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OrgUnitDTO:
    """Reactivate an archived OrgUnit (D6, AC-8)."""
    try:
        return svc.reactivate_org_unit(ctx, org_unit_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="OrgUnit not found")


@router.patch("/org-units/{org_unit_id}/reorder", response_model=OrgUnitDTO)
def reorder_org_unit(
    org_unit_id: uuid.UUID,
    dto: OrgUnitReorderDTO,
    ctx: TenantContext = Depends(get_tenant_context),
    svc: TenantInstitutionService = Depends(get_tenant_institution_service),
) -> OrgUnitDTO:
    """Reorder an OrgUnit (D6)."""
    try:
        return svc.reorder_org_unit(ctx, org_unit_id, dto.sort_order)
    except ValueError:
        raise HTTPException(status_code=404, detail="OrgUnit not found")
