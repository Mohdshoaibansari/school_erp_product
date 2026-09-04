"""C-05 Academic Structure — CurriculumVersionService."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.academic.models.curriculum_version import CurriculumVersion
from kernel.academic.repos.curriculum_version_repo import CurriculumVersionRepo


class CurriculumVersionService:
    """Service for CurriculumVersion entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurriculumVersionRepo(db)

    def create_curriculum_version(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        curriculum_id: uuid.UUID,
        name: str,
    ) -> CurriculumVersion:
        """Create a new CurriculumVersion.

        Version number is auto-incremented.
        """
        # Get next version number
        latest_version = self.repo.get_latest_version_number(curriculum_id)
        next_version = latest_version + 1

        return self.repo.create(
            client_id=client_id,
            institution_id=institution_id,
            curriculum_id=curriculum_id,
            version_number=next_version,
            name=name,
        )

    def get_by_id(self, version_id: uuid.UUID) -> CurriculumVersion | None:
        return self.repo.get_by_id(version_id)

    def list_by_curriculum(self, curriculum_id: uuid.UUID) -> Sequence[CurriculumVersion]:
        return self.repo.list_by_curriculum(curriculum_id)
