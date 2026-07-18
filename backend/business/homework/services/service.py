"""Homework module — service layer."""

from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy.orm import Session, sessionmaker
from kernel.tenant_context import TenantContext
from kernel.audit import AuditEmitter
from business.homework.repos.homework_repos import HomeworkRepository, SubmissionRepository, GradeRepository
from business.homework.services.dtos import *


class HomeworkService:
    STUDENT_ROLES = {"Student", "Parent"}

    def __init__(self, session_factory: sessionmaker[Session] | None = None,
                 audit_emitter: AuditEmitter | None = None):
        self._session_factory = session_factory
        self._audit = audit_emitter
        self._hw_repo = HomeworkRepository()
        self._sub_repo = SubmissionRepository()
        self._grade_repo = GradeRepository()

    # -- Homework CRUD --
    def create_homework(self, ctx: TenantContext, dto: HomeworkCreateDTO) -> HomeworkDTO:
        with self._session_factory() as s:
            r = self._hw_repo.create(s, ctx, dto); s.commit()
            if self._audit: self._audit.emit(action="homework_created", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"homework_id": str(r.id), "title": r.title, "grade_level": r.grade_level or "", "subject": r.subject or "", "due_date": str(r.due_date)})
            return r

    def list_homeworks(self, ctx: TenantContext, subject: str | None = None, grade_level: str | None = None, status: str | None = None) -> list[HomeworkDTO]:
        with self._session_factory() as s:
            return self._hw_repo.list_filtered(s, ctx, subject, grade_level, status)

    def get_homework(self, ctx: TenantContext, hw_id: uuid.UUID) -> HomeworkDTO | None:
        with self._session_factory() as s:
            return self._hw_repo.get(s, ctx, hw_id)

    def update_homework(self, ctx: TenantContext, hw_id: uuid.UUID, dto: HomeworkUpdateDTO) -> HomeworkDTO:
        with self._session_factory() as s:
            r = self._hw_repo.update(s, ctx, hw_id, dto); s.commit()
            if self._audit: self._audit.emit(action="homework_updated", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"homework_id": str(r.id)})
            return r

    def delete_homework(self, ctx: TenantContext, hw_id: uuid.UUID) -> None:
        with self._session_factory() as s:
            self._hw_repo.update(s, ctx, hw_id, HomeworkUpdateDTO(status="archived")); s.commit()

    def close_homework(self, ctx: TenantContext, hw_id: uuid.UUID) -> HomeworkDTO:
        with self._session_factory() as s:
            r = self._hw_repo.close(s, ctx, hw_id); s.commit()
            if self._audit: self._audit.emit(action="homework_closed", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"homework_id": str(r.id)})
            return r

    # -- Submission --
    def submit(self, ctx: TenantContext, dto: SubmissionCreateDTO) -> SubmissionDTO:
        with self._session_factory() as s:
            hw = self._hw_repo.get(s, ctx, dto.homework_id)
            if not hw: raise ValueError("Homework not found")
            if hw.status != "active": raise ValueError("Homework is closed")
            status = "late" if datetime.utcnow().date() > hw.due_date else "submitted"
            r = self._sub_repo.create(s, ctx, dto, status); s.commit()
            if self._audit: self._audit.emit(action="submission_created", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"submission_id": str(r.id), "homework_id": str(dto.homework_id), "student_id": str(r.student_id), "status": status})
            return r

    def list_submissions(self, ctx: TenantContext, homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None, status: str | None = None) -> list[SubmissionDTO]:
        self._enforce_ownership(ctx, student_id)
        with self._session_factory() as s:
            return self._sub_repo.list_filtered(s, ctx, homework_id, student_id, status)

    def get_submission(self, ctx: TenantContext, sub_id: uuid.UUID) -> SubmissionDTO | None:
        with self._session_factory() as s:
            r = self._sub_repo.get(s, ctx, sub_id)
            if r: self._enforce_ownership(ctx, r.student_id)
            return r

    # -- Grading --
    def grade_submission(self, ctx: TenantContext, sub_id: uuid.UUID, dto: GradeCreateDTO) -> GradeDTO:
        with self._session_factory() as s:
            sub = self._sub_repo.get(s, ctx, sub_id)
            if not sub: raise ValueError("Submission not found")
            hw = self._hw_repo.get(s, ctx, sub.homework_id)
            r = self._grade_repo.create(s, ctx, sub_id, dto, hw.max_score if hw else None)
            # Auto-update submission status
            obj = s.get(Submission, sub_id); obj.status = "graded"
            s.flush(); s.commit()
            if self._audit: self._audit.emit(action="grade_created", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"grade_id": str(r.id), "submission_id": str(sub_id), "score": r.score, "max_score": r.max_score or 0})
            return r

    def list_grades(self, ctx: TenantContext, submission_id: uuid.UUID | None = None, homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None) -> list[GradeDTO]:
        self._enforce_ownership(ctx, student_id)
        with self._session_factory() as s:
            return self._grade_repo.list_filtered(s, ctx, submission_id, homework_id, student_id)

    def update_grade(self, ctx: TenantContext, grade_id: uuid.UUID, dto: GradeUpdateDTO) -> GradeDTO:
        with self._session_factory() as s:
            r = self._grade_repo.update(s, ctx, grade_id, dto); s.commit()
            if self._audit: self._audit.emit(action="grade_updated", client_id=ctx.client_id, institution_id=ctx.institution_id, actor=ctx.user_id or "system", payload={"grade_id": str(r.id), "score": r.score})
            return r

    # -- Ownership --
    def _enforce_ownership(self, ctx: TenantContext, requested_student_id: uuid.UUID | None) -> None:
        if requested_student_id and ctx.roles:
            if any(r in self.STUDENT_ROLES for r in ctx.roles):
                if str(requested_student_id) != str(ctx.user_id):
                    raise ValueError("You can only access your own records")
