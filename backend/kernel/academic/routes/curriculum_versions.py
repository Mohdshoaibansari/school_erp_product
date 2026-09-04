"""C-05 Academic Structure — CurriculumVersion routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.curriculum_version_service import CurriculumVersionService
from kernel.academic.services.dtos import CurriculumVersionCreateDTO, CurriculumVersionDTO

router = APIRouter(prefix="/api/v1/curricula/{curriculum_id}/versions", tags=["curriculum-versions"])


@router.post("", response_model=CurriculumVersionDTO, status_code=status.HTTP_201_CREATED, summary="Create curriculum version")
def create_curriculum_version(
    curriculum_id: uuid.UUID,
    dto: CurriculumVersionCreateDTO,
    _authz: None = Depends(require_permission("curriculum_version", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> CurriculumVersionDTO:
    """Create a new CurriculumVersion (auto-increments version number)."""
    try:
        cv_svc = CurriculumVersionService(svc.db)
        cv = cv_svc.create_curriculum_version(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            curriculum_id=curriculum_id,
            name=dto.name,
        )
        svc.db.commit()
        return CurriculumVersionDTO.model_validate(cv)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[CurriculumVersionDTO], summary="List curriculum versions")
def list_curriculum_versions(
    curriculum_id: uuid.UUID,
    _authz: None = Depends(require_permission("curriculum_version", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[CurriculumVersionDTO]:
    """List CurriculumVersions for a Curriculum."""
    cv_svc = CurriculumVersionService(svc.db)
    cvs = cv_svc.list_by_curriculum(curriculum_id)
    return [CurriculumVersionDTO.model_validate(cv) for cv in cvs]
