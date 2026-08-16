"""C-05 Academic Structure — Enrollment repo (T17)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.student_enrollment import StudentEnrollment


class EnrollmentRepo:
    """Repository for StudentEnrollment entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        student_id: uuid.UUID,
        section_id: uuid.UUID,
        status: str = "active",
    ) -> StudentEnrollment:
        enrollment = StudentEnrollment(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            student_id=student_id,
            section_id=section_id,
            status=status,
        )
        self.db.add(enrollment)
        self.db.flush()
        return enrollment

    def get_by_id(self, enrollment_id: uuid.UUID) -> StudentEnrollment | None:
        return self.db.get(StudentEnrollment, enrollment_id)

    def list_by_section(self, section_id: uuid.UUID, status: str | None = "active") -> Sequence[StudentEnrollment]:
        stmt = select(StudentEnrollment).where(StudentEnrollment.section_id == section_id)
        if status:
            stmt = stmt.where(StudentEnrollment.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_student(self, student_id: uuid.UUID, academic_year_id: uuid.UUID | None = None) -> Sequence[StudentEnrollment]:
        stmt = select(StudentEnrollment).where(StudentEnrollment.student_id == student_id)
        if academic_year_id:
            stmt = stmt.where(StudentEnrollment.academic_year_id == academic_year_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[StudentEnrollment]:
        stmt = select(StudentEnrollment).where(StudentEnrollment.academic_year_id == academic_year_id)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, enrollment: StudentEnrollment, **kwargs) -> StudentEnrollment:
        for key, value in kwargs.items():
            setattr(enrollment, key, value)
        self.db.flush()
        return enrollment

    def deactivate(self, enrollment: StudentEnrollment, new_status: str = "transferred") -> StudentEnrollment:
        enrollment.status = new_status
        self.db.flush()
        return enrollment
