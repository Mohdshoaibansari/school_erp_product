"""C-05 Academic Structure — AcademicService.

Core CRUD services for all academic entities.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.class_academic_year import ClassAcademicYear

from kernel.academic.repos.academic_repo import AcademicYearRepo, TermRepo
from kernel.academic.repos.structure_repo import GradeLevelRepo, ClassRepo, SectionRepo
from kernel.academic.repos.subject_repo import SubjectRepo
from kernel.academic.repos.class_academic_year_repo import ClassAcademicYearRepo

from kernel.academic.services.lifecycle_service import LifecycleService
from kernel.academic.services.dtos import (
    AcademicYearCreateDTO, AcademicYearDTO, AcademicYearTransitionDTO,
)


class AcademicService:
    """Main service for C-05 Academic Structure."""

    def __init__(self, db: Session):
        self.db = db
        self.year_repo = AcademicYearRepo(db)
        self.term_repo = TermRepo(db)
        self.grade_repo = GradeLevelRepo(db)
        self.class_repo = ClassRepo(db)
        self.section_repo = SectionRepo(db)
        self.subject_repo = SubjectRepo(db)
        self.class_academic_year_repo = ClassAcademicYearRepo(db)
        self.lifecycle_service = LifecycleService(db)

    # ============================================================
    # AcademicYear
    # ============================================================

    def create_academic_year(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        dto: AcademicYearCreateDTO,
    ) -> AcademicYear:
        """Create a new AcademicYear.

        Auto-creates ClassAcademicYear for every existing Class.
        """
        # Validate no overlap
        if self.year_repo.check_overlap(institution_id, dto.start_date, dto.end_date):
            raise ValueError("AcademicYear dates overlap with an existing AcademicYear")

        # Create the year record
        year = self.year_repo.create(client_id, institution_id, dto.name, dto.start_date, dto.end_date)

        # Auto-create ClassAcademicYear for every existing Class
        classes = self.class_repo.list_by_institution(institution_id)
        for cls in classes:
            self.class_academic_year_repo.create(
                client_id=client_id,
                institution_id=institution_id,
                class_id=cls.id,
                academic_year_id=year.id,
                offered=True,  # Default to offered
            )

        self.db.commit()
        return year

    def get_academic_year(self, year_id: uuid.UUID) -> AcademicYear | None:
        return self.year_repo.get_by_id(year_id)

    def list_academic_years(self, institution_id: uuid.UUID, status: str | None = None) -> Sequence[AcademicYear]:
        return self.year_repo.list_by_institution(institution_id, status)

    def transition_academic_year(
        self,
        year_id: uuid.UUID,
        dto: AcademicYearTransitionDTO,
    ) -> AcademicYear:
        year = self.year_repo.get_by_id(year_id)
        if not year:
            raise ValueError(f"AcademicYear {year_id} not found")
        result = self.lifecycle_service.transition(year, dto.new_state, dto.reason)
        self.db.commit()
        return result
