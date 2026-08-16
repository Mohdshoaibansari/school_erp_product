"""C-05 Academic Structure — Assignment repo (T18)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.teacher_assignment import TeacherAssignment


class AssignmentRepo:
    """Repository for TeacherAssignment entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        teacher_id: uuid.UUID,
        section_id: uuid.UUID,
        subject_id: uuid.UUID,
        status: str = "active",
    ) -> TeacherAssignment:
        assignment = TeacherAssignment(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            teacher_id=teacher_id,
            section_id=section_id,
            subject_id=subject_id,
            status=status,
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def get_by_id(self, assignment_id: uuid.UUID) -> TeacherAssignment | None:
        return self.db.get(TeacherAssignment, assignment_id)

    def list_by_section(self, section_id: uuid.UUID, status: str | None = "active") -> Sequence[TeacherAssignment]:
        stmt = select(TeacherAssignment).where(TeacherAssignment.section_id == section_id)
        if status:
            stmt = stmt.where(TeacherAssignment.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_teacher(self, teacher_id: uuid.UUID, academic_year_id: uuid.UUID | None = None) -> Sequence[TeacherAssignment]:
        stmt = select(TeacherAssignment).where(TeacherAssignment.teacher_id == teacher_id)
        if academic_year_id:
            stmt = stmt.where(TeacherAssignment.academic_year_id == academic_year_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[TeacherAssignment]:
        stmt = select(TeacherAssignment).where(TeacherAssignment.academic_year_id == academic_year_id)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, assignment: TeacherAssignment, **kwargs) -> TeacherAssignment:
        for key, value in kwargs.items():
            setattr(assignment, key, value)
        self.db.flush()
        return assignment

    def deactivate(self, assignment: TeacherAssignment) -> TeacherAssignment:
        assignment.status = "inactive"
        self.db.flush()
        return assignment
