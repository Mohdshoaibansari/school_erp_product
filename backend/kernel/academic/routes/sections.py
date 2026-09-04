"""C-05 Academic Structure — Section routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import SectionCreateDTO, SectionDTO

router = APIRouter(prefix="/api/v1/class-academic-years/{cay_id}/sections", tags=["sections"])


@router.post("", response_model=SectionDTO, status_code=status.HTTP_201_CREATED, summary="Create section")
def create_section(
    cay_id: uuid.UUID,
    dto: SectionCreateDTO,
    _authz: None = Depends(require_permission("section", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> SectionDTO:
    """Create a Section under a ClassAcademicYear."""
    try:
        section = svc.section_repo.create(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            class_academic_year_id=cay_id,
            name=dto.name,
            sort_order=dto.sort_order,
        )
        svc.db.commit()
        return SectionDTO.model_validate(section)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[SectionDTO], summary="List sections")
def list_sections(
    cay_id: uuid.UUID,
    _authz: None = Depends(require_permission("section", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[SectionDTO]:
    """List Sections for a ClassAcademicYear."""
    sections = svc.section_repo.list_by_class_academic_year(cay_id)
    return [SectionDTO.model_validate(s) for s in sections]
