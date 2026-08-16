"""C-05 Academic Structure — Structure repos (T15) for GradeLevel, Class, Section."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.academic.models.grade_level import GradeLevel
from kernel.academic.models.class_entity import ClassEntity
from kernel.academic.models.section import Section


class GradeLevelRepo:
    """Repository for GradeLevel entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
    ) -> GradeLevel:
        gl = GradeLevel(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            name=name,
            sort_order=sort_order,
        )
        self.db.add(gl)
        self.db.flush()
        return gl

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[GradeLevel]:
        stmt = select(GradeLevel).where(GradeLevel.academic_year_id == academic_year_id).order_by(GradeLevel.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, gl_id: uuid.UUID) -> GradeLevel | None:
        return self.db.get(GradeLevel, gl_id)


class ClassRepo:
    """Repository for Class entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        grade_level_id: uuid.UUID,
        name: str,
        sort_order: int = 0,
    ) -> ClassEntity:
        cls = ClassEntity(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            grade_level_id=grade_level_id,
            name=name,
            sort_order=sort_order,
        )
        self.db.add(cls)
        self.db.flush()
        return cls

    def list_by_grade_level(self, grade_level_id: uuid.UUID) -> Sequence[ClassEntity]:
        stmt = select(ClassEntity).where(ClassEntity.grade_level_id == grade_level_id).order_by(ClassEntity.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[ClassEntity]:
        stmt = select(ClassEntity).where(ClassEntity.academic_year_id == academic_year_id).order_by(ClassEntity.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, cls_id: uuid.UUID) -> ClassEntity | None:
        return self.db.get(ClassEntity, cls_id)


class SectionRepo:
    """Repository for Section entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        class_id: uuid.UUID,
        name: str,
        homeroom_teacher_id: uuid.UUID | None = None,
        sort_order: int = 0,
    ) -> Section:
        section = Section(
            client_id=client_id,
            institution_id=institution_id,
            academic_year_id=academic_year_id,
            class_id=class_id,
            name=name,
            homeroom_teacher_id=homeroom_teacher_id,
            sort_order=sort_order,
        )
        self.db.add(section)
        self.db.flush()
        return section

    def list_by_class(self, class_id: uuid.UUID) -> Sequence[Section]:
        stmt = select(Section).where(Section.class_id == class_id).order_by(Section.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[Section]:
        stmt = select(Section).where(Section.academic_year_id == academic_year_id).order_by(Section.sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, section_id: uuid.UUID) -> Section | None:
        return self.db.get(Section, section_id)

    def update(self, section: Section, **kwargs) -> Section:
        for key, value in kwargs.items():
            setattr(section, key, value)
        self.db.flush()
        return section
