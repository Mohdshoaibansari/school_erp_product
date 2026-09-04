"""C-05 Academic Structure — CurriculumService."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from kernel.academic.models.curriculum import Curriculum
from kernel.academic.repos.curriculum_repo import CurriculumRepo


class CurriculumService:
    """Service for Curriculum entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurriculumRepo(db)

    def create_curriculum(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        name: str,
    ) -> Curriculum:
        """Create a Curriculum for a GradeLevel."""
        # Check if already exists
        existing = self.repo.get_by_grade_level(grade_level_id)
        if existing:
            raise ValueError(f"Curriculum already exists for GradeLevel {grade_level_id}")

        return self.repo.create(
            client_id=client_id,
            institution_id=institution_id,
            grade_level_id=grade_level_id,
            name=name,
        )

    def get_by_id(self, curriculum_id: uuid.UUID) -> Curriculum | None:
        return self.repo.get_by_id(curriculum_id)

    def get_by_grade_level(self, grade_level_id: uuid.UUID) -> Curriculum | None:
        return self.repo.get_by_grade_level(grade_level_id)
