"""C-05 Academic Structure — Curriculum repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.curriculum import Curriculum


class CurriculumRepo:
    """Repository for Curriculum entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        name: str,
    ) -> Curriculum:
        curriculum = Curriculum(
            client_id=client_id,
            institution_id=institution_id,
            grade_level_id=grade_level_id,
            name=name,
        )
        self.db.add(curriculum)
        self.db.flush()
        return curriculum

    def get_by_id(self, curriculum_id: uuid.UUID) -> Curriculum | None:
        return self.db.get(Curriculum, curriculum_id)

    def get_by_grade_level(self, grade_level_id: uuid.UUID) -> Curriculum | None:
        stmt = select(Curriculum).where(Curriculum.grade_level_id == grade_level_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_institution(self, institution_id: uuid.UUID) -> Sequence[Curriculum]:
        stmt = select(Curriculum).where(Curriculum.institution_id == institution_id)
        return list(self.db.execute(stmt).scalars().all())
