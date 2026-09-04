"""C-05 Academic Structure — Term routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import TermCreateDTO, TermDTO

router = APIRouter(prefix="/api/v1/academic-years/{year_id}/terms", tags=["terms"])


@router.post("", response_model=TermDTO, status_code=status.HTTP_201_CREATED, summary="Create term")
def create_term(
    year_id: uuid.UUID,
    dto: TermCreateDTO,
    _authz: None = Depends(require_permission("academic_year", "update")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> TermDTO:
    """Create a Term within an AcademicYear."""
    try:
        term = svc.term_repo.create(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            academic_year_id=year_id,
            name=dto.name,
            start_date=dto.start_date,
            end_date=dto.end_date,
            sort_order=dto.sort_order,
        )
        svc.db.commit()
        return TermDTO.model_validate(term)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[TermDTO], summary="List terms")
def list_terms(
    year_id: uuid.UUID,
    _authz: None = Depends(require_permission("academic_year", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[TermDTO]:
    """List Terms for an AcademicYear."""
    terms = svc.term_repo.list_by_academic_year(year_id)
    return [TermDTO.model_validate(t) for t in terms]
