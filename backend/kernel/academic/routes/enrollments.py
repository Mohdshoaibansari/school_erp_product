"""C-05 Academic Structure — Enrollment routes (T25)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import StudentEnrollmentCreateDTO, StudentEnrollmentDTO

router = APIRouter(prefix="/api/v1", tags=["enrollments"])


@router.post("/sections/{section_id}/enrollments", response_model=StudentEnrollmentDTO, status_code=status.HTTP_201_CREATED, summary="Enroll student in section")
def enroll_student(
    section_id: uuid.UUID,
    dto: StudentEnrollmentCreateDTO,
    _authz: None = Depends(require_permission("enrollment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> StudentEnrollmentDTO:
    """Enroll a student in a section."""
    # Get academic year from section
    section = svc.section_repo.get_by_id(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    dto.section_id = section_id
    try:
        enrollment = svc.enroll_student(ctx.client_id, ctx.institution_id, section.academic_year_id, dto)
        return StudentEnrollmentDTO.model_validate(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sections/{section_id}/enrollments", response_model=list[StudentEnrollmentDTO], summary="List section enrollments")
def list_enrollments(
    section_id: uuid.UUID,
    _authz: None = Depends(require_permission("enrollment", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[StudentEnrollmentDTO]:
    """List enrollments for a section."""
    enrollments = svc.list_enrollments(section_id)
    return [StudentEnrollmentDTO.model_validate(e) for e in enrollments]


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove enrollment")
def remove_enrollment(
    enrollment_id: uuid.UUID,
    _authz: None = Depends(require_permission("enrollment", "update")),
    svc: AcademicService = Depends(get_academic_service),
) -> None:
    """Remove enrollment (set status to withdrawn)."""
    enrollment = svc.enrollment_repo.get_by_id(enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    svc.enrollment_repo.deactivate(enrollment, "withdrawn")
