"""Homework module — routes."""
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

@hw_router.post("", response_model=HomeworkDTO, status_code=status.HTTP_201_CREATED)
def create_homework(dto: HomeworkCreateDTO, _a: None = Depends(require_permission("homework", "create")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.create_homework(ctx, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@hw_router.get("", response_model=list[HomeworkDTO])
def list_homeworks(subject: str | None = None, grade_level: str | None = None, status: str | None = None,
                   _a: None = Depends(require_permission("homework", "read")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    return svc.list_homeworks(ctx, subject, grade_level, status)

@hw_router.get("/{hw_id}", response_model=HomeworkDTO)
def get_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "read")),
                 ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    r = svc.get_homework(ctx, hw_id)
    if not r: raise HTTPException(404, "Homework not found")
    return r

@hw_router.patch("/{hw_id}", response_model=HomeworkDTO)
def update_homework(hw_id: uuid.UUID, dto: HomeworkUpdateDTO,
                    _a: None = Depends(require_permission("homework", "update")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.update_homework(ctx, hw_id, dto)
    except ValueError: raise HTTPException(404, "Homework not found")

@hw_router.delete("/{hw_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "delete")),
                    ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    svc.delete_homework(ctx, hw_id)

@hw_router.post("/{hw_id}/close", response_model=HomeworkDTO)
def close_homework(hw_id: uuid.UUID, _a: None = Depends(require_permission("homework", "close")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.close_homework(ctx, hw_id)
    except ValueError as e: raise HTTPException(400, detail=str(e))

# -- Submissions --
sub_router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])

@sub_router.post("", response_model=SubmissionDTO, status_code=status.HTTP_201_CREATED)
def submit(dto: SubmissionCreateDTO, _a: None = Depends(require_permission("submission", "create")),
           ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.submit(ctx, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@sub_router.get("", response_model=list[SubmissionDTO])
def list_submissions(homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None, status: str | None = None,
                     _a: None = Depends(require_permission("submission", "read")),
                     ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.list_submissions(ctx, homework_id, student_id, status)
    except ValueError as e: raise HTTPException(403, detail=str(e))

@sub_router.get("/{sub_id}", response_model=SubmissionDTO)
def get_submission(sub_id: uuid.UUID, _a: None = Depends(require_permission("submission", "read")),
                   ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    r = svc.get_submission(ctx, sub_id)
    if not r: raise HTTPException(404, "Submission not found")
    return r

# -- Grades --
grade_router = APIRouter(prefix="/api/v1", tags=["grades"])

@grade_router.post("/submissions/{sub_id}/grade", response_model=GradeDTO, status_code=status.HTTP_201_CREATED)
def grade_submission(sub_id: uuid.UUID, dto: GradeCreateDTO,
                     _a: None = Depends(require_permission("grade", "create")),
                     ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.grade_submission(ctx, sub_id, dto)
    except ValueError as e: raise HTTPException(400, detail=str(e))

@grade_router.get("/grades", response_model=list[GradeDTO])
def list_grades(submission_id: uuid.UUID | None = None, homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None,
                _a: None = Depends(require_permission("grade", "read")),
                ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.list_grades(ctx, submission_id, homework_id, student_id)
    except ValueError as e: raise HTTPException(403, detail=str(e))

@grade_router.patch("/grades/{grade_id}", response_model=GradeDTO)
def update_grade(grade_id: uuid.UUID, dto: GradeUpdateDTO,
                 _a: None = Depends(require_permission("grade", "update")),
                 ctx: TenantContext = Depends(get_tenant_context), svc: HomeworkService = Depends(get_homework_service)):
    try: return svc.update_grade(ctx, grade_id, dto)
    except ValueError: raise HTTPException(404, "Grade not found")
