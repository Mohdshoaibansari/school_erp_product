"""C-05 Academic Structure — ClassAcademicYear repo."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.class_academic_year import ClassAcademicYear


class ClassAcademicYearRepo:
    """Repository for ClassAcademicYear entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        class_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        offered: bool = True,
    ) -> ClassAcademicYear:
        cay = ClassAcademicYear(
            client_id=client_id,
            institution_id=institution_id,
            class_id=class_id,
            academic_year_id=academic_year_id,
            offered=offered,
        )
        self.db.add(cay)
        self.db.flush()
        return cay

    def get_by_id(self, cay_id: uuid.UUID) -> ClassAcademicYear | None:
        return self.db.get(ClassAcademicYear, cay_id)

    def get_by_class_and_year(
        self, class_id: uuid.UUID, academic_year_id: uuid.UUID
    ) -> ClassAcademicYear | None:
        stmt = select(ClassAcademicYear).where(
            ClassAcademicYear.class_id == class_id,
            ClassAcademicYear.academic_year_id == academic_year_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[ClassAcademicYear]:
        stmt = (
            select(ClassAcademicYear)
            .where(ClassAcademicYear.academic_year_id == academic_year_id)
            .order_by(ClassAcademicYear.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_by_class(self, class_id: uuid.UUID) -> Sequence[ClassAcademicYear]:
        stmt = (
            select(ClassAcademicYear)
            .where(ClassAcademicYear.class_id == class_id)
            .order_by(ClassAcademicYear.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def update(self, cay: ClassAcademicYear, **kwargs) -> ClassAcademicYear:
        for key, value in kwargs.items():
            setattr(cay, key, value)
        self.db.flush()
        return cay
