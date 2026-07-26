"""Homework module routes — homework, submissions, and grades (D1-D16)."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from kernel.tenant_context import TenantContext, get_tenant_context
from kernel.authz.dependencies import require_permission
from business.homework.dependencies import get_homework_service
from business.homework.services.service import HomeworkService
from business.homework.services.dtos import *

# -- Homeworks --
hw_router = APIRouter(prefix="/api/v1/homeworks", tags=["homeworks"])

@hw_router.post("", response_model=HomeworkDTO, status_code=status.HTTP_201_CREATED, summary="Create homework")
def create_homework(dto: HomeworkCreateDTO, _a: None = Depends(require_permission("homework", "create")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Create a new homework assignment. Late flag computed at creation (D12).

    Permission: homework.create. Returns 400 on validation errors.
    """
    try: return svc.create_homework(ctx, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@hw_router.get("", response_model=list[HomeworkDTO], summary="List homeworks")
def list_homeworks(subject: str | None = None, grade_level: str | None = None, status: str | None = None,
                   _a: None = Depends(require_permission("homework", "read")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """List homeworks, optionally filtered by subject, grade_level, or status.

    Permission: homework.read. Tenant-scoped.
    """
    return svc.list_homeworks(ctx, subject, grade_level, status)

@hw_router.get("/{hw_id}", response_model=HomeworkDTO, summary="Get homework")
def get_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "read")),
                 ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Get a single homework by ID. Returns 404 if not found.

    Permission: homework.read.
    """
    r = svc.get_homework(ctx, hw_id)
    if not r: raise HTTPException(404, "Homework not found")
    return r

@hw_router.patch("/{hw_id}", response_model=HomeworkDTO, summary="Update homework")
def update_homework(hw_id: uuid.UUID, dto: HomeworkUpdateDTO,
                    _a: None = Depends(require_permission("homework", "update")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Update homework fields (title, description, due_date, max_score).

    Permission: homework.update. Returns 404 if not found.
    """
    try: return svc.update_homework(ctx, hw_id, dto)
    except ValueError: raise HTTPException(404, "Homework not found")

@hw_router.delete("/{hw_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete homework")
def delete_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "delete")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Delete a homework assignment.

    Permission: homework.delete.
    """
    svc.delete_homework(ctx, hw_id)

@hw_router.post("/{hw_id}/close", response_model=HomeworkDTO, summary="Close homework")
def close_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "close")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Close a homework (active → closed). No more submissions accepted after.

    Permission: homework.close. Returns 400 on validation errors.
    """
    try: return svc.close_homework(ctx, hw_id)
    except ValueError as e: raise HTTPException(400, detail=str(e))

# -- Submissions --
sub_router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])

@sub_router.post("", response_model=SubmissionDTO, status_code=status.HTTP_201_CREATED, summary="Submit homework")
def submit(dto: SubmissionCreateDTO, _a: None = Depends(require_permission("submission", "create")),
           ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Submit homework as a student. Status auto-updates based on due date (D6).

    Permission: submission.create. Returns 400 on validation errors.
    """
    try: return svc.submit(ctx, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@sub_router.get("", response_model=list[SubmissionDTO], summary="List submissions")
def list_submissions(homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None, status: str | None = None,
                     _a: None = Depends(require_permission("submission", "read")),
                     ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """List submissions, optionally filtered by homework_id, student_id, or status.

    Permission: submission.read. Students see only their own submissions.
    """
    try: return svc.list_submissions(ctx, homework_id, student_id, status)
    except ValueError as e: raise HTTPException(403, detail=str(e))

@sub_router.get("/{sub_id}", response_model=SubmissionDTO, summary="Get submission")
def get_submission(sub_id: uuid.UUID, _a: None = Depends(require_permission("submission", "read")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Get a single submission by ID. Returns 404 if not found.

    Permission: submission.read.
    """
    r = svc.get_submission(ctx, sub_id)
    if not r: raise HTTPException(404, "Submission not found")
    return r

# -- Grades --
grade_router = APIRouter(prefix="/api/v1", tags=["grades"])

@grade_router.post("/submissions/{sub_id}/grade", response_model=GradeDTO, status_code=status.HTTP_201_CREATED, summary="Grade submission")
def grade_submission(sub_id: uuid.UUID, dto: GradeCreateDTO,
                     _a: None = Depends(require_permission("grade", "create")),
                     ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Grade a submission. Submissions status auto-updates to "graded" (D6).

    Permission: grade.create. Returns 400 on validation errors.
    """
    try: return svc.grade_submission(ctx, sub_id, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@grade_router.get("/grades", response_model=list[GradeDTO], summary="List grades")
def list_grades(submission_id: uuid.UUID | None = None, homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None,
                _a: None = Depends(require_permission("grade", "read")),
                ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """List grades, optionally filtered by submission_id, homework_id, or student_id.

    Permission: grade.read. Students see only their own grades.
    """
    try: return svc.list_grades(ctx, submission_id, homework_id, student_id)
    except ValueError as e: raise HTTPException(403, detail=str(e))

@grade_router.patch("/grades/{grade_id}", response_model=GradeDTO, summary="Update grade")
def update_grade(grade_id: uuid.UUID, dto: GradeUpdateDTO,
                 _a: None = Depends(require_permission("grade", "update")),
                 ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    """Update a grade (score, feedback).

    Permission: grade.update. Returns 404 if not found.
    """
    try: return svc.update_grade(ctx, grade_id, dto)
    except ValueError: raise HTTPException(404, "Grade not found")