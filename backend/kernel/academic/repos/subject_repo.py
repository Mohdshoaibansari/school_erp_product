"""C-05 Academic Structure — Subject repos (T16)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.subject import Subject
from kernel.academic.models.subject_group import SubjectGroup, SubjectGroupMember


class SubjectRepo:
    """Repository for Subject entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        name: str,
        code: str | None = None,
        sort_order: int = 0,
    ) -> Subject:
        subject = Subject(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            name=name,
            code=code,
            sort_order=sort_order,
        )
        self.db.add(subject)
        self.db.flush()
        return subject

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[Subject]:
        stmt = select(Subject).where(Subject.academic_year_id == academic_year_id).order_by(Subject.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, subject_id: uuid.UUID) -> Subject | None:
        return self.db.get(Subject, subject_id)


class SubjectGroupRepo:
    """Repository for SubjectGroup and SubjectGroupMember entities."""

    def __init__(self, db: Session):
        self.db = db

    def create_group(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        name: str,
    ) -> SubjectGroup:
        group = SubjectGroup(
            client_id=client_id,
            institution_id=institution_id,
            name=name,
        )
        self.db.add(group)
        self.db.flush()
        return group

    def add_member(self, subject_group_id: uuid.UUID, subject_id: uuid.UUID) -> SubjectGroupMember:
        member = SubjectGroupMember(
            subject_group_id=subject_group_id,
            subject_id=subject_id,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def list_groups(self, institution_id: uuid.UUID) -> Sequence[SubjectGroup]:
        stmt = select(SubjectGroup).where(SubjectGroup.institution_id == institution_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_members(self, subject_group_id: uuid.UUID) -> Sequence[SubjectGroupMember]:
        stmt = select(SubjectGroupMember).where(SubjectGroupMember.subject_group_id == subject_group_id)
        return list(self.db.execute(stmt).scalars().all())
