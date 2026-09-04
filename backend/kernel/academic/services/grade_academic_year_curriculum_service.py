"""C-05 Academic Structure — GradeAcademicYearCurriculumService."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from kernel.academic.models.grade_academic_year_curriculum import GradeAcademicYearCurriculum
from kernel.academic.repos.grade_academic_year_curriculum_repo import GradeAcademicYearCurriculumRepo


class GradeAcademicYearCurriculumService:
    """Service for GradeAcademicYearCurriculum entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = GradeAcademicYearCurriculumRepo(db)

    def assign_curriculum_version(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        curriculum_version_id: uuid.UUID,
    ) -> GradeAcademicYearCurriculum:
        """Assign a CurriculumVersion to a Grade for an AcademicYear.

        One CurriculumVersion per Grade per AcademicYear.
        """
        # Check if already assigned
        existing = self.repo.get_by_grade_and_year(grade_level_id, academic_year_id)
        if existing:
            # Update existing assignment
            existing.curriculum_version_id = curriculum_version_id
            self.db.flush()
            return existing

        return self.repo.create(
            client_id=client_id,
            institution_id=institution_id,
            grade_level_id=grade_level_id,
            academic_year_id=academic_year_id,
            curriculum_version_id=curriculum_version_id,
        )

    def get_by_id(self, gayc_id: uuid.UUID) -> GradeAcademicYearCurriculum | None:
        return self.repo.get_by_id(gayc_id)

    def get_by_grade_and_year(
        self,
        grade_level_id: uuid.UUID,
        academic_year_id: uuid.UUID,
    ) -> GradeAcademicYearCurriculum | None:
        return self.repo.get_by_grade_and_year(grade_level_id, academic_year_id)
