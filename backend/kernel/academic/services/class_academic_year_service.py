"""C-05 Academic Structure — ClassAcademicYearService."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.academic.models.class_academic_year import ClassAcademicYear
from kernel.academic.repos.class_academic_year_repo import ClassAcademicYearRepo
from kernel.academic.repos.structure_repo import SectionRepo


class ClassAcademicYearService:
    """Service for ClassAcademicYear entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ClassAcademicYearRepo(db)
        self.section_repo = SectionRepo(db)

    def add_class_to_academic_year(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        class_id: uuid.UUID,
        academic_year_id: uuid.UUID,
    ) -> ClassAcademicYear:
        """Add a Class to an existing Planning AcademicYear."""
        # Check if already exists
        existing = self.repo.get_by_class_and_year(class_id, academic_year_id)
        if existing:
            raise ValueError("Class already added to this AcademicYear")

        return self.repo.create(
            client_id=client_id,
            institution_id=institution_id,
            class_id=class_id,
            academic_year_id=academic_year_id,
            offered=True,
        )

    def update_offered(
        self,
        class_academic_year_id: uuid.UUID,
        offered: bool,
    ) -> ClassAcademicYear:
        """Update offered flag for a ClassAcademicYear."""
        cay = self.repo.get_by_id(class_academic_year_id)
        if not cay:
            raise ValueError(f"ClassAcademicYear {class_academic_year_id} not found")

        # If setting to false, validate no sections exist
        if not offered:
            sections = self.section_repo.list_by_class_academic_year(class_academic_year_id)
            if sections:
                raise ValueError(
                    "Cannot set offered=false: Sections exist for this ClassAcademicYear. "
                    "Remove all Sections first."
                )

        return self.repo.update(cay, offered=offered)

    def get_by_id(self, cay_id: uuid.UUID) -> ClassAcademicYear | None:
        return self.repo.get_by_id(cay_id)

    def list_by_academic_year(self, academic_year_id: uuid.UUID) -> Sequence[ClassAcademicYear]:
        return self.repo.list_by_academic_year(academic_year_id)

    def list_by_class(self, class_id: uuid.UUID) -> Sequence[ClassAcademicYear]:
        return self.repo.list_by_class(class_id)
