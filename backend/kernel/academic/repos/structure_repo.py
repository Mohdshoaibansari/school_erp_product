"""C-05 Academic Structure — Structure repos for GradeLevel, Class, Section."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.grade_level import GradeLevel
from kernel.academic.models.class_entity import Class
from kernel.academic.models.section import Section


class GradeLevelRepo:
    """Repository for GradeLevel entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        name: str,
        org_unit_id: uuid.UUID | None = None,
        sort_order: int = 0,
    ) -> GradeLevel:
        gl = GradeLevel(
            client_id=client_id,
            institution_id=institution_id,
            org_unit_id=org_unit_id,
            name=name,
            sort_order=sort_order,
        )
        self.db.add(gl)
        self.db.flush()
        return gl

    def list_by_institution(self, institution_id: uuid.UUID) -> Sequence[GradeLevel]:
        stmt = select(GradeLevel).where(GradeLevel.institution_id == institution_id).order_by(GradeLevel.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, gl_id: uuid.UUID) -> GradeLevel | None:
        return self.db.get(GradeLevel, gl_id)

    def update(self, grade_level: GradeLevel, **kwargs) -> GradeLevel:
        for key, value in kwargs.items():
            setattr(grade_level, key, value)
        self.db.flush()
        return grade_level


class ClassRepo:
    """Repository for Class entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
    ) -> Class:
        cls = Class(
            client_id=client_id,
            institution_id=institution_id,
            grade_level_id=grade_level_id,
            name=name,
            sort_order=sort_order,
        )
        self.db.add(cls)
        self.db.flush()
        return cls

    def list_by_grade_level(self, grade_level_id: uuid.UUID) -> Sequence[Class]:
        stmt = select(Class).where(Class.grade_level_id == grade_level_id).order_by(Class.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_institution(self, institution_id: uuid.UUID) -> Sequence[Class]:
        stmt = select(Class).where(Class.institution_id == institution_id).order_by(Class.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, cls_id: uuid.UUID) -> Class | None:
        return self.db.get(Class, cls_id)

    def update(self, cls: Class, **kwargs) -> Class:
        for key, value in kwargs.items():
            setattr(cls, key, value)
        self.db.flush()
        return cls


class SectionRepo:
    """Repository for Section entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        class_academic_year_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
    ) -> Section:
        section = Section(
            client_id=client_id,
            institution_id=institution_id,
            class_academic_year_id=class_academic_year_id,
            name=name,
            sort_order=sort_order,
        )
        self.db.add(section)
        self.db.flush()
        return section

    def list_by_class_academic_year(self, class_academic_year_id: uuid.UUID) -> Sequence[Section]:
        stmt = select(Section).where(Section.class_academic_year_id == class_academic_year_id).order_by(Section.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, section_id: uuid.UUID) -> Section | None:
        return self.db.get(Section, section_id)

    def update(self, section: Section, **kwargs) -> Section:
        for key, value in kwargs.items():
            setattr(section, key, value)
        self.db.flush()
        return section

    def delete(self, section: Section) -> None:
        self.db.delete(section)
        self.db.flush()
