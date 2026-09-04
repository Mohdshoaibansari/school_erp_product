"""C-05 Academic Structure — SectionSubjectService."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.academic.models.section_subject import SectionSubject
from kernel.academic.repos.section_subject_repo import SectionSubjectRepo
from kernel.academic.repos.structure_repo import SectionRepo
from kernel.academic.repos.subject_repo import SubjectRepo
from kernel.academic.repos.class_academic_year_repo import ClassAcademicYearRepo
from kernel.academic.repos.grade_academic_year_curriculum_repo import GradeAcademicYearCurriculumRepo


class SectionSubjectService:
    """Service for SectionSubject entity."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SectionSubjectRepo(db)
        self.section_repo = SectionRepo(db)
        self.subject_repo = SubjectRepo(db)
        self.cay_repo = ClassAcademicYearRepo(db)
        self.gayc_repo = GradeAcademicYearCurriculumRepo(db)

    def assign_subject_to_section(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        section_id: uuid.UUID,
        subject_id: uuid.UUID,
    ) -> SectionSubject:
        """Assign a Subject to a Section.

        Validates that the Subject belongs to the applicable Grade CurriculumVersion.
        """
        # Check if already assigned
        existing = self.repo.get_by_section_and_subject(section_id, subject_id)
        if existing:
            if existing.is_active:
                raise ValueError("Subject already assigned to this Section")
            # Reactivate if was disabled
            return self.repo.update(existing, is_active=True)

        # Validate subject belongs to applicable CurriculumVersion
        self._validate_subject_for_section(section_id, subject_id)

        return self.repo.create(
            client_id=client_id,
            institution_id=institution_id,
            section_id=section_id,
            subject_id=subject_id,
        )

    def disable_subject_for_section(
        self,
        section_subject_id: uuid.UUID,
    ) -> SectionSubject:
        """Disable a Subject for a Section (soft delete)."""
        ss = self.repo.get_by_id(section_subject_id)
        if not ss:
            raise ValueError(f"SectionSubject {section_subject_id} not found")

        return self.repo.update(ss, is_active=False)

    def remove_subject_from_section(
        self,
        section_subject_id: uuid.UUID,
    ) -> None:
        """Remove a Subject from a Section (hard delete)."""
        ss = self.repo.get_by_id(section_subject_id)
        if not ss:
            raise ValueError(f"SectionSubject {section_subject_id} not found")

        self.repo.delete(ss)

    def list_by_section(
        self,
        section_id: uuid.UUID,
        active_only: bool = True,
    ) -> Sequence[SectionSubject]:
        return self.repo.list_by_section(section_id, active_only)

    def _validate_subject_for_section(
        self,
        section_id: uuid.UUID,
        subject_id: uuid.UUID,
    ) -> None:
        """Validate that a Subject belongs to the applicable Grade CurriculumVersion.

        Flow:
        1. Section → ClassAcademicYear → Class → GradeLevel
        2. GradeLevel + AcademicYear → GradeAcademicYearCurriculum → CurriculumVersion
        3. Validate Subject belongs to that CurriculumVersion
        """
        # Get Section
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ValueError(f"Section {section_id} not found")

        # Get ClassAcademicYear
        cay = self.cay_repo.get_by_id(section.class_academic_year_id)
        if not cay:
            raise ValueError("ClassAcademicYear not found")

        # Get GradeLevel through Class
        from kernel.academic.repos.structure_repo import ClassRepo
        class_repo = ClassRepo(self.db)
        cls = class_repo.get_by_id(cay.class_id)
        if not cls:
            raise ValueError("Class not found")

        # Get GradeAcademicYearCurriculum
        gayc = self.gayc_repo.get_by_grade_and_year(cls.grade_level_id, cay.academic_year_id)
        if not gayc:
            raise ValueError(
                "No CurriculumVersion assigned to this Grade for this AcademicYear. "
                "Assign a CurriculumVersion first."
            )

        # Validate Subject belongs to the CurriculumVersion
        subject = self.subject_repo.get_by_id(subject_id)
        if not subject:
            raise ValueError(f"Subject {subject_id} not found")

        if subject.curriculum_version_id != gayc.curriculum_version_id:
            raise ValueError(
                f"Subject '{subject.name}' does not belong to the applicable CurriculumVersion. "
                "Only subjects from the assigned CurriculumVersion can be added to Sections."
            )
