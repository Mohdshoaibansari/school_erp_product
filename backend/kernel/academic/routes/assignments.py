"""C-05 Academic Structure — TeacherAssignment routes (T26)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from kernel.academic.dependencies import get_academic_service
from kernel.academic.services.service import AcademicService
from kernel.academic.services.dtos import TeacherAssignmentCreateDTO, TeacherAssignmentDTO

router = APIRouter(prefix="/api/v1/teacher-assignments", tags=["teacher-assignments"])


@router.post("", response_model=TeacherAssignmentDTO, status_code=status.HTTP_201_CREATED, summary="Assign teacher to subject")
def assign_teacher(
    dto: TeacherAssignmentCreateDTO,
    _authz: None = Depends(require_permission("teacher_assignment", "create")),
    ctx: TenantContext = Depends(get_tenant_context),
    svc: AcademicService = Depends(get_academic_service),
) -> TeacherAssignmentDTO:
    """Assign a teacher to a subject in a section."""
    # Get academic year from section
    section = svc.section_repo.get_by_id(dto.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    try:
        assignment = svc.assign_teacher(ctx.client_id, ctx.institution_id, section.academic_year_id, dto)
        return TeacherAssignmentDTO.model_validate(assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[TeacherAssignmentDTO], summary="List teacher assignments")
def list_teacher_assignments(
    section_id: uuid.UUID | None = None,
    teacher_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
    _authz: None = Depends(require_permission("teacher_assignment", "read")),
    svc: AcademicService = Depends(get_academic_service),
) -> list[TeacherAssignmentDTO]:
    """List teacher assignments with optional filters."""
    assignments = svc.list_teacher_assignments(section_id, teacher_id, academic_year_id)
    return [TeacherAssignmentDTO.model_validate(a) for a in assignments]


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove teacher assignment")
def remove_teacher_assignment(
    assignment_id: uuid.UUID,
    _authz: None = Depends(require_permission("teacher_assignment", "update")),
    svc: AcademicService = Depends(get_academic_service),
) -> None:
    """Remove teacher assignment (set status to inactive)."""
    try:
        svc.remove_teacher_assignment(assignment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
