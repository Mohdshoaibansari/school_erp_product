"""C-05 Academic Structure — Subject routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import SubjectCreateDTO, SubjectDTO

router = APIRouter(prefix="/api/v1/curriculum-versions/{cv_id}/subjects", tags=["subjects"])


@router.post("", response_model=SubjectDTO, status_code=status.HTTP_201_CREATED, summary="Create subject")
def create_subject(
    cv_id: uuid.UUID,
    dto: SubjectCreateDTO,
    _authz: None = Depends(require_permission("curriculum", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> SubjectDTO:
    """Create a Subject under a CurriculumVersion."""
    try:
        subject = svc.subject_repo.create(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            curriculum_version_id=cv_id,
            name=dto.name,
            code=dto.code,
            sort_order=dto.sort_order,
        )
        svc.db.commit()
        return SubjectDTO.model_validate(subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[SubjectDTO], summary="List subjects")
def list_subjects(
    cv_id: uuid.UUID,
    _authz: None = Depends(require_permission("curriculum", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[SubjectDTO]:
    """List Subjects for a CurriculumVersion."""
    subjects = svc.subject_repo.list_by_curriculum_version(cv_id)
    return [SubjectDTO.model_validate(s) for s in subjects]
