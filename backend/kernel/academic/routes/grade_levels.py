"""C-05 Academic Structure — GradeLevel routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import GradeLevelCreateDTO, GradeLevelDTO

router = APIRouter(prefix="/api/v1/grade-levels", tags=["grade-levels"])


@router.post("", response_model=GradeLevelDTO, status_code=status.HTTP_201_CREATED, summary="Create grade level")
def create_grade_level(
    dto: GradeLevelCreateDTO,
    _authz: None = Depends(require_permission("academic_year", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> GradeLevelDTO:
    """Create a GradeLevel (permanent master)."""
    try:
        gl = svc.grade_repo.create(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            name=dto.name,
            org_unit_id=dto.org_unit_id,
            sort_order=dto.sort_order,
        )
        svc.db.commit()
        return GradeLevelDTO.model_validate(gl)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[GradeLevelDTO], summary="List grade levels")
def list_grade_levels(
    _authz: None = Depends(require_permission("academic_year", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> list[GradeLevelDTO]:
    """List GradeLevels for the institution."""
    gls = svc.grade_repo.list_by_institution(ctx.institution_id)
    return [GradeLevelDTO.model_validate(gl) for gl in gls]
