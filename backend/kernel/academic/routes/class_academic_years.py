"""C-05 Academic Structure — ClassAcademicYear routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.class_academic_year_service import ClassAcademicYearService
from kernel.academic.services.dtos import ClassAcademicYearDTO

router = APIRouter(prefix="/api/v1/academic-years/{year_id}/classes", tags=["class-academic-years"])


@router.post("", response_model=ClassAcademicYearDTO, status_code=status.HTTP_201_CREATED, summary="Add class to academic year")
def add_class_to_academic_year(
    year_id: uuid.UUID,
    class_id: uuid.UUID,
    _authz: None = Depends(require_permission("class_academic_year", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> ClassAcademicYearDTO:
    """Add a Class to an existing Planning AcademicYear."""
    try:
        cay_svc = ClassAcademicYearService(svc.db)
        cay = cay_svc.add_class_to_academic_year(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            class_id=class_id,
            academic_year_id=year_id,
        )
        svc.db.commit()
        return ClassAcademicYearDTO.model_validate(cay)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ClassAcademicYearDTO], summary="List class academic years")
def list_class_academic_years(
    year_id: uuid.UUID,
    _authz: None = Depends(require_permission("class_academic_year", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[ClassAcademicYearDTO]:
    """List ClassAcademicYears for an AcademicYear."""
    cay_svc = ClassAcademicYearService(svc.db)
    cays = cay_svc.list_by_academic_year(year_id)
    return [ClassAcademicYearDTO.model_validate(cay) for cay in cays]
