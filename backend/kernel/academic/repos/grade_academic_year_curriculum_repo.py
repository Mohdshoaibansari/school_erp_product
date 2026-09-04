"""C-05 Academic Structure — GradeAcademicYearCurriculum repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.grade_academic_year_curriculum import GradeAcademicYearCurriculum


class GradeAcademicYearCurriculumRepo:
    """Repository for GradeAcademicYearCurriculum entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        curriculum_version_id: uuid.UUID,
    ) -> GradeAcademicYearCurriculum:
        gayc = GradeAcademicYearCurriculum(
            client_id=client_id,
            institution_id=institution_id,
            grade_level_id=grade_level_id,
            academic_year_id=academic_year_id,
            curriculum_version_id=curriculum_version_id,
        )
        self.db.add(gayc)
        self.db.flush()
        return gayc

    def get_by_id(self, gayc_id: uuid.UUID) -> GradeAcademicYearCurriculum | None:
        return self.db.get(GradeAcademicYearCurriculum, gayc_id)

    def get_by_grade_and_year(
        self, grade_level_id: uuid.UUID, academic_year_id: uuid.UUID
    ) -> GradeAcademicYearCurriculum | None:
        stmt = select(GradeAcademicYearCurriculum).where(
            GradeAcademicYearCurriculum.grade_level_id == grade_level_id,
            GradeAcademicYearCurriculum.academic_year_id == academic_year_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_grade(self, grade_level_id: uuid.UUID) -> Sequence[GradeAcademicYearCurriculum]:
        stmt = select(GradeAcademicYearCurriculum).where(
            GradeAcademicYearCurriculum.grade_level_id == grade_level_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[GradeAcademicYearCurriculum]:
        stmt = select(GradeAcademicYearCurriculum).where(
            GradeAcademicYearCurriculum.academic_year_id == academic_year_id
        )
        return list(self.db.execute(stmt).scalars().all())
