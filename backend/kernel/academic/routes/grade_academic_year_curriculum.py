"""C-05 Academic Structure — GradeAcademicYearCurriculum routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.grade_academic_year_curriculum_service import GradeAcademicYearCurriculumService
from kernel.academic.services.dtos import GradeAcademicYearCurriculumAssignDTO, GradeAcademicYearCurriculumDTO

router = APIRouter(
    prefix="/api/v1/grade-levels/{grade_level_id}/academic-years/{year_id}/curriculum",
    tags=["grade-academic-year-curriculum"],
)


@router.post("", response_model=GradeAcademicYearCurriculumDTO, status_code=status.HTTP_201_CREATED, summary="Assign curriculum version")
def assign_curriculum_version(
    grade_level_id: uuid.UUID,
    year_id: uuid.UUID,
    dto: GradeAcademicYearCurriculumAssignDTO,
    _authz: None = Depends(require_permission("curriculum", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> GradeAcademicYearCurriculumDTO:
    """Assign a CurriculumVersion to a Grade for an AcademicYear."""
    try:
        gayc_svc = GradeAcademicYearCurriculumService(svc.db)
        gayc = gayc_svc.assign_curriculum_version(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            grade_level_id=grade_level_id,
            academic_year_id=year_id,
            curriculum_version_id=dto.curriculum_version_id,
        )
        svc.db.commit()
        return GradeAcademicYearCurriculumDTO.model_validate(gayc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=GradeAcademicYearCurriculumDTO | None, summary="Get assigned curriculum version")
def get_assigned_curriculum_version(
    grade_level_id: uuid.UUID,
    year_id: uuid.UUID,
    _authz: None = Depends(require_permission("curriculum", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> GradeAcademicYearCurriculumDTO | None:
    """Get the CurriculumVersion assigned to a Grade for an AcademicYear."""
    gayc_svc = GradeAcademicYearCurriculumService(svc.db)
    gayc = gayc_svc.get_by_grade_and_year(grade_level_id, year_id)
    if not gayc:
        return None
    return GradeAcademicYearCurriculumDTO.model_validate(gayc)
