"""C-05 Academic Structure — AcademicYear routes (T24)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import (
    AcademicYearCreateDTO, AcademicYearDTO, AcademicYearTransitionDTO,
    AcademicStructureDTO,
)

router = APIRouter(prefix="/api/v1/academic-years", tags=["academic-years"])


@router.post("", response_model=AcademicYearDTO, status_code=status.HTTP_201_CREATED, summary="Create academic year")
def create_academic_year(
    dto: AcademicYearCreateDTO,
    _authz: None = Depends(require_permission("academic_year", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> AcademicYearDTO:
    """Create a new AcademicYear. Clones from previous year or generates from template."""
    try:
        year = svc.create_academic_year(ctx.client_id, ctx.institution_id, dto)
        return AcademicYearDTO.model_validate(year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[AcademicYearDTO], summary="List academic years")
def list_academic_years(
    status_filter: str | None = None,
    _authz: None = Depends(require_permission("academic_year", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> list[AcademicYearDTO]:
    """List AcademicYears for the institution."""
    years = svc.list_academic_years(ctx.institution_id, status_filter)
    return [AcademicYearDTO.model_validate(y) for y in years]


@router.get("/{year_id}", response_model=AcademicYearDTO, summary="Get academic year")
def get_academic_year(
    year_id: uuid.UUID,
    _authz: None = Depends(require_permission("academic_year", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> AcademicYearDTO:
    """Get AcademicYear by ID."""
    year = svc.get_academic_year(year_id)
    if not year:
        raise HTTPException(status_code=404, detail="AcademicYear not found")
    return AcademicYearDTO.model_validate(year)


@router.post("/{year_id}/transition", response_model=AcademicYearDTO, summary="Transition academic year lifecycle")
def transition_academic_year(
    year_id: uuid.UUID,
    dto: AcademicYearTransitionDTO,
    _authz: None = Depends(require_permission("academic_year", "transition")),
    svc: AcademicService = Depends(get_academic_service),
) -> AcademicYearDTO:
    """Transition AcademicYear lifecycle (planning → active → closed)."""
    try:
        year = svc.transition_academic_year(year_id, dto)
        return AcademicYearDTO.model_validate(year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{year_id}/structure", response_model=AcademicStructureDTO, summary="Get full academic structure")
def get_academic_structure(
    year_id: uuid.UUID,
    _authz: None = Depends(require_permission("academic_year", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> AcademicStructureDTO:
    """Get full academic structure (terms, grades, classes, sections, subjects)."""
    try:
        return svc.get_full_structure(year_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
