"""C-05 Academic Structure — CurriculumVersion repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.curriculum_version import CurriculumVersion


class CurriculumVersionRepo:
    """Repository for CurriculumVersion entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        curriculum_id: uuid.UUID,
        version_number: int,
        name: str,
    ) -> CurriculumVersion:
        version = CurriculumVersion(
            client_id=client_id,
            institution_id=institution_id,
            curriculum_id=curriculum_id,
            version_number=version_number,
            name=name,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def get_by_id(self, version_id: uuid.UUID) -> CurriculumVersion | None:
        return self.db.get(CurriculumVersion, version_id)

    def list_by_curriculum(self, curriculum_id: uuid.UUID) -> Sequence[CurriculumVersion]:
        stmt = (
            select(CurriculumVersion)
            .where(CurriculumVersion.curriculum_id == curriculum_id)
            .order_by(CurriculumVersion.version_number)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_version_number(self, curriculum_id: uuid.UUID) -> int:
        stmt = (
            select(CurriculumVersion.version_number)
            .where(CurriculumVersion.curriculum_id == curriculum_id)
            .order_by(CurriculumVersion.version_number.desc())
            .limit(1)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return result or 0
