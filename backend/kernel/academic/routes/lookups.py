"""C-05 Academic Structure — lookup routes (T27)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import SubjectDTO, SubjectGroupDTO

router = APIRouter(prefix="/api/v1", tags=["academic-lookups"])


@router.get("/subjects", response_model=list[SubjectDTO], summary="List subjects")
def list_subjects(
    academic_year_id: uuid.UUID | None = None,
    _authz: None = Depends(require_permission("academic_year", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> list[SubjectDTO]:
    """List subjects, optionally filtered by academic year."""
    # If no year specified, get active year
    if not academic_year_id:
        active_year = svc.year_repo.get_active(ctx.institution_id)
        if active_year:
            academic_year_id = active_year.id
        else:
            return []

    subjects = svc.subject_repo.list_by_academic_year(academic_year_id)
    return [SubjectDTO.model_validate(s) for s in subjects]


@router.get("/subject-groups", response_model=list[SubjectGroupDTO], summary="List subject groups")
def list_subject_groups(
    _authz: None = Depends(require_permission("academic_year", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> list[SubjectGroupDTO]:
    """List subject groups for the institution."""
    groups = svc.subject_group_repo.list_groups(ctx.institution_id)
    return [SubjectGroupDTO.model_validate(g) for g in groups]
