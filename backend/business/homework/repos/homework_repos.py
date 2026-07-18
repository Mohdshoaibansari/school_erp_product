"""Homework module — repositories."""

from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.tenant_context import TenantContext
from business.homework.models.homework_models import Homework, Submission, Grade
from business.homework.services.dtos import (
    HomeworkCreateDTO, HomeworkDTO, HomeworkUpdateDTO,
    SubmissionCreateDTO, SubmissionDTO, GradeCreateDTO, GradeDTO, GradeUpdateDTO,
)


class HomeworkRepository(TenantAwareRepositoryBase[Homework]):
    def __init__(self): super().__init__(Homework)

    def _to_dto(self, obj: Homework) -> HomeworkDTO:
        return HomeworkDTO(
            id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
            title=obj.title, description=obj.description, subject=obj.subject,
            grade_level=obj.grade_level, section=obj.section, due_date=obj.due_date,
            max_score=obj.max_score, status=obj.status, assigned_by=obj.assigned_by,
            created_at=obj.created_at,
        )

    def create(self, session: Session, ctx: TenantContext, dto: HomeworkCreateDTO) -> HomeworkDTO:
        obj = Homework(client_id=ctx.client_id, institution_id=ctx.institution_id,
                       title=dto.title, description=dto.description, subject=dto.subject,
                       grade_level=dto.grade_level, section=dto.section,
                       due_date=dto.due_date, max_score=dto.max_score,
                       assigned_by=uuid.UUID(ctx.user_id) if ctx.user_id else None)
        session.add(obj); session.flush(); return self._to_dto(obj)

    def list_filtered(self, session: Session, ctx: TenantContext,
                      subject: str | None = None, grade_level: str | None = None,
                      status: str | None = None) -> list[HomeworkDTO]:
        stmt = select(Homework)
        stmt = self._apply_tenant_filter(stmt, ctx)
        if subject: stmt = stmt.where(Homework.subject == subject)
        if grade_level: stmt = stmt.where(Homework.grade_level == grade_level)
        if status: stmt = stmt.where(Homework.status == status)
        else: stmt = stmt.where(Homework.status.in_(["active", "closed"]))
        stmt = stmt.order_by(Homework.created_at.desc())
        rows = session.execute(stmt).scalars().all()
        return [self._to_dto(r) for r in rows]

    def close(self, session: Session, ctx: TenantContext, hw_id: uuid.UUID) -> HomeworkDTO:
        obj = session.get(Homework, hw_id)
        if not obj: raise ValueError("Not found")
        obj.status = "closed"; session.flush(); return self._to_dto(obj)


class SubmissionRepository(TenantAwareRepositoryBase[Submission]):
    def __init__(self): super().__init__(Submission)

    def _to_dto(self, obj: Submission) -> SubmissionDTO:
        return SubmissionDTO(id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
                             homework_id=obj.homework_id, student_id=obj.student_id,
                             content=obj.content, status=obj.status,
                             submitted_at=obj.submitted_at, created_at=obj.created_at)

    def create(self, session: Session, ctx: TenantContext, dto: SubmissionCreateDTO, status: str) -> SubmissionDTO:
        obj = Submission(client_id=ctx.client_id, institution_id=ctx.institution_id,
                         homework_id=dto.homework_id, student_id=uuid.UUID(ctx.user_id) if ctx.user_id else None,
                         content=dto.content, status=status, submitted_at=datetime.utcnow())
        session.add(obj); session.flush(); return self._to_dto(obj)

    def list_filtered(self, session: Session, ctx: TenantContext,
                      homework_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None,
                      status: str | None = None) -> list[SubmissionDTO]:
        stmt = select(Submission)
        stmt = self._apply_tenant_filter(stmt, ctx)
        if homework_id: stmt = stmt.where(Submission.homework_id == homework_id)
        if student_id: stmt = stmt.where(Submission.student_id == student_id)
        if status: stmt = stmt.where(Submission.status == status)
        stmt = stmt.order_by(Submission.submitted_at.desc())
        return [self._to_dto(r) for r in session.execute(stmt).scalars().all()]


class GradeRepository(TenantAwareRepositoryBase[Grade]):
    def __init__(self): super().__init__(Grade)

    def _to_dto(self, obj: Grade) -> GradeDTO:
        return GradeDTO(id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
                        submission_id=obj.submission_id, score=obj.score, max_score=obj.max_score,
                        feedback=obj.feedback, graded_by=obj.graded_by,
                        graded_at=obj.graded_at, created_at=obj.created_at)

    def create(self, session: Session, ctx: TenantContext, submission_id: uuid.UUID,
               dto: GradeCreateDTO, max_score: int | None) -> GradeDTO:
        obj = Grade(client_id=ctx.client_id, institution_id=ctx.institution_id,
                    submission_id=submission_id, score=dto.score, max_score=max_score,
                    feedback=dto.feedback,
                    graded_by=uuid.UUID(ctx.user_id) if ctx.user_id else None,
                    graded_at=datetime.utcnow())
        session.add(obj); session.flush(); return self._to_dto(obj)

    def list_filtered(self, session: Session, ctx: TenantContext,
                      submission_id: uuid.UUID | None = None, homework_id: uuid.UUID | None = None,
                      student_id: uuid.UUID | None = None) -> list[GradeDTO]:
        stmt = select(Grade)
        if student_id:
            stmt = stmt.join(Submission).where(Submission.student_id == student_id)
        if homework_id:
            stmt = stmt.join(Submission).where(Submission.homework_id == homework_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        if submission_id: stmt = stmt.where(Grade.submission_id == submission_id)
        return [self._to_dto(r) for r in session.execute(stmt).scalars().all()]
