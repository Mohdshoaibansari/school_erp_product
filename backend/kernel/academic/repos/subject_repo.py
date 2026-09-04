"""C-05 Academic Structure — Subject repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.subject import Subject


class SubjectRepo:
    """Repository for Subject entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        curriculum_version_id: uuid.UUID,
        name: str,
        code: str | None = None,
        sort_order: int = 0,
    ) -> Subject:
        subject = Subject(
            client_id=client_id,
            institution_id=institution_id,
            curriculum_version_id=curriculum_version_id,
            name=name,
            code=code,
            sort_order=sort_order,
        )
        self.db.add(subject)
        self.db.flush()
        return subject

    def list_by_curriculum_version(self, curriculum_version_id: uuid.UUID) -> Sequence[Subject]:
        stmt = select(Subject).where(Subject.curriculum_version_id == curriculum_version_id).order_by(Subject.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, subject_id: uuid.UUID) -> Subject | None:
        return self.db.get(Subject, subject_id)

    def update(self, subject: Subject, **kwargs) -> Subject:
        for key, value in kwargs.items():
            setattr(subject, key, value)
        self.db.flush()
        return subject
