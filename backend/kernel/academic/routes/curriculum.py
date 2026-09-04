"""C-05 Academic Structure — Curriculum routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.curriculum_service import CurriculumService
from kernel.academic.services.dtos import CurriculumCreateDTO, CurriculumDTO

router = APIRouter(prefix="/api/v1/grade-levels/{grade_level_id}/curriculum", tags=["curriculum"])


@router.post("", response_model=CurriculumDTO, status_code=status.HTTP_201_CREATED, summary="Create curriculum")
def create_curriculum(
    grade_level_id: uuid.UUID,
    dto: CurriculumCreateDTO,
    _authz: None = Depends(require_permission("curriculum", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> CurriculumDTO:
    """Create a Curriculum for a GradeLevel."""
    try:
        curriculum_svc = CurriculumService(svc.db)
        curriculum = curriculum_svc.create_curriculum(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            grade_level_id=grade_level_id,
            name=dto.name,
        )
        svc.db.commit()
        return CurriculumDTO.model_validate(curriculum)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=CurriculumDTO | None, summary="Get curriculum")
def get_curriculum(
    grade_level_id: uuid.UUID,
    _authz: None = Depends(require_permission("curriculum", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> CurriculumDTO | None:
    """Get Curriculum for a GradeLevel."""
    curriculum_svc = CurriculumService(svc.db)
    curriculum = curriculum_svc.get_by_grade_level(grade_level_id)
    if not curriculum:
        return None
    return CurriculumDTO.model_validate(curriculum)
