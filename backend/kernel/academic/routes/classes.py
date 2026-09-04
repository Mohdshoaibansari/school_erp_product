"""C-05 Academic Structure — Class routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import ClassCreateDTO, ClassDTO

router = APIRouter(prefix="/api/v1/classes", tags=["classes"])


@router.post("", response_model=ClassDTO, status_code=status.HTTP_201_CREATED, summary="Create class")
def create_class(
    dto: ClassCreateDTO,
    _authz: None = Depends(require_permission("academic_year", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> ClassDTO:
    """Create a Class (permanent master)."""
    try:
        cls = svc.class_repo.create(
            client_id=ctx.client_id,
            institution_id=ctx.institution_id,
            grade_level_id=dto.grade_level_id,
            name=dto.name,
            sort_order=dto.sort_order,
        )
        svc.db.commit()
        return ClassDTO.model_validate(cls)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ClassDTO], summary="List classes")
def list_classes(
    grade_level_id: uuid.UUID | None = None,
    _authz: None = Depends(require_permission("academic_year", "read")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> list[ClassDTO]:
    """List Classes for the institution or a specific GradeLevel."""
    if grade_level_id:
        classes = svc.class_repo.list_by_grade_level(grade_level_id)
    else:
        classes = svc.class_repo.list_by_institution(ctx.institution_id)
    return [ClassDTO.model_validate(c) for c in classes]
