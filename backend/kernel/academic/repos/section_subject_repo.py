"""C-05 Academic Structure — SectionSubject repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.section_subject import SectionSubject


class SectionSubjectRepo:
    """Repository for SectionSubject entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        section_id: uuid.UUID,
        subject_id: uuid.UUID,
    ) -> SectionSubject:
        ss = SectionSubject(
            client_id=client_id,
            institution_id=institution_id,
            section_id=section_id,
            subject_id=subject_id,
            is_active=True,
        )
        self.db.add(ss)
        self.db.flush()
        return ss

    def get_by_id(self, ss_id: uuid.UUID) -> SectionSubject | None:
        return self.db.get(SectionSubject, ss_id)

    def get_by_section_and_subject(
        self, section_id: uuid.UUID, subject_id: uuid.UUID
    ) -> SectionSubject | None:
        stmt = select(SectionSubject).where(
            SectionSubject.section_id == section_id,
            SectionSubject.subject_id == subject_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_section(self, section_id: uuid.UUID, active_only: bool = True) -> Sequence[SectionSubject]:
        stmt = select(SectionSubject).where(SectionSubject.section_id == section_id)
        if active_only:
            stmt = stmt.where(SectionSubject.is_active == True)
        return list(self.db.execute(stmt).scalars().all())

    def update(self, ss: SectionSubject, **kwargs) -> SectionSubject:
        for key, value in kwargs.items():
            setattr(ss, key, value)
        self.db.flush()
        return ss

    def delete(self, ss: SectionSubject) -> None:
        self.db.delete(ss)
        self.db.flush()
