"""C-05 Academic Structure — SectionSubject routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.section_subject_service import SectionSubjectService
from kernel.academic.services.dtos import SectionSubjectCreateDTO, SectionSubjectDTO

router = APIRouter(prefix="/api/v1/sections/{section_id}/subjects", tags=["section-subjects"])


@router.post("", response_model=SectionSubjectDTO, status_code=status.HTTP_201_CREATED, summary="Assign subject to section")
def assign_subject_to_section(
    section_id: uuid.UUID,
    dto: SectionSubjectCreateDTO,
    _authz: None = Depends(require_permission("section_subject", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> SectionSubjectDTO:
    """Assign a Subject to a Section (validates against CurriculumVersion)."""
    try:
        ss_svc = SectionSubjectService(svc.db)
        ss = ss_svc.assign_subject_to_section(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            section_id=section_id,
            subject_id=dto.subject_id,
        )
        svc.db.commit()
        return SectionSubjectDTO.model_validate(ss)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[SectionSubjectDTO], summary="List section subjects")
def list_section_subjects(
    section_id: uuid.UUID,
    active_only: bool = True,
    _authz: None = Depends(require_permission("section_subject", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[SectionSubjectDTO]:
    """List Subjects for a Section."""
    ss_svc = SectionSubjectService(svc.db)
    subjects = ss_svc.list_by_section(section_id, active_only)
    return [SectionSubjectDTO.model_validate(s) for s in subjects]
