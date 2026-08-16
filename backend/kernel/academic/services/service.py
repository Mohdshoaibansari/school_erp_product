"""C-05 Academic Structure — AcademicService (T22).

Core CRUD services for all academic entities.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.student_enrollment import StudentEnrollment
from kernel.academic.models.teacher_assignment import TeacherAssignment

from kernel.academic.repos.academic_repo import AcademicYearRepo, TermRepo
from kernel.academic.repos.structure_repo import GradeLevelRepo, ClassRepo, SectionRepo
from kernel.academic.repos.subject_repo import SubjectRepo, SubjectGroupRepo
from kernel.academic.repos.enrollment_repo import EnrollmentRepo
from kernel.academic.repos.assignment_repo import AssignmentRepo

from kernel.academic.services.template_service import TemplateService
from kernel.academic.services.clone_service import CloneService
from kernel.academic.services.lifecycle_service import LifecycleService
from kernel.academic.services.dtos import (
    AcademicYearCreateDTO, AcademicYearDTO, AcademicYearTransitionDTO,
    StudentEnrollmentCreateDTO, StudentEnrollmentDTO,
    TeacherAssignmentCreateDTO, TeacherAssignmentDTO,
    SectionUpdateDTO, AcademicStructureDTO,
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
        self.subject_group_repo = SubjectGroupRepo(db)
        self.enrollment_repo = EnrollmentRepo(db)
        self.assignment_repo = AssignmentRepo(db)
        self.template_service = TemplateService(db)
        self.clone_service = CloneService(db)
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

        If clone_from is specified, clones from that year.
        Otherwise clones from latest closed year, or uses template if first year.
        """
        # Create the year record
        year = self.year_repo.create(client_id, institution_id, dto.name, dto.start_date, dto.end_date)

        # Determine source for cloning
        if dto.clone_from:
            source_year_id = dto.clone_from
        else:
            latest_closed = self.clone_service.find_latest_closed_year(institution_id)
            if latest_closed:
                source_year_id = latest_closed.id
            else:
                source_year_id = None

        # Clone or generate from template
        if source_year_id:
            self.clone_service.clone_from_year(source_year_id, year.id, client_id, institution_id)
        else:
            self.template_service.generate_from_template(year.id, client_id, institution_id, dto.start_date, dto.end_date)

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
        return self.lifecycle_service.transition(year, dto.new_state, dto.reason)

    # ============================================================
    # Structure (GradeLevel, Class, Section)
    # ============================================================

    def get_full_structure(self, academic_year_id: uuid.UUID) -> AcademicStructureDTO:
        """Get full academic structure for a year."""
        year = self.year_repo.get_by_id(academic_year_id)
        if not year:
            raise ValueError(f"AcademicYear {academic_year_id} not found")

        return AcademicStructureDTO(
            academic_year=AcademicYearDTO.model_validate(year),
            terms=[t for t in self.term_repo.list_by_academic_year(academic_year_id)],
            grade_levels=[gl for gl in self.grade_repo.list_by_academic_year(academic_year_id)],
            classes=[c for c in self.class_repo.list_by_academic_year(academic_year_id)],
            sections=[s for s in self.section_repo.list_by_academic_year(academic_year_id)],
            subjects=[s for s in self.subject_repo.list_by_academic_year(academic_year_id)],
        )

    def update_section(self, section_id: uuid.UUID, dto: SectionUpdateDTO):
        section = self.section_repo.get_by_id(section_id)
        if not section:
            raise ValueError(f"Section {section_id} not found")
        return self.section_repo.update(section, homeroom_teacher_id=dto.homeroom_teacher_id)

    # ============================================================
    # Enrollment
    # ============================================================

    def enroll_student(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        dto: StudentEnrollmentCreateDTO,
    ) -> StudentEnrollment:
        """Enroll a student in a section."""
        section = self.section_repo.get_by_id(dto.section_id)
        if not section:
            raise ValueError(f"Section {dto.section_id} not found")

        return self.enrollment_repo.create(
            client_id, institution_id, academic_year_id,
            dto.student_id, dto.section_id,
        )

    def list_enrollments(self, section_id: uuid.UUID) -> Sequence[StudentEnrollment]:
        return self.enrollment_repo.list_by_section(section_id)

    def transfer_enrollment(self, enrollment_id: uuid.UUID, new_section_id: uuid.UUID) -> tuple[StudentEnrollment, StudentEnrollment]:
        """Transfer student to a new section (deactivate old, create new)."""
        old_enrollment = self.enrollment_repo.get_by_id(enrollment_id)
        if not old_enrollment:
            raise ValueError(f"Enrollment {enrollment_id} not found")

        # Deactivate old
        self.enrollment_repo.deactivate(old_enrollment, "transferred")

        # Create new
        new_enrollment = self.enrollment_repo.create(
            old_enrollment.client_id, old_enrollment.institution_id,
            old_enrollment.academic_year_id, old_enrollment.student_id,
            new_section_id, "active",
        )

        return old_enrollment, new_enrollment

    # ============================================================
    # Teacher Assignment
    # ============================================================

    def assign_teacher(
        self,
        client_id: uuid.UUID,
        institution_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        dto: TeacherAssignmentCreateDTO,
    ) -> TeacherAssignment:
        """Assign a teacher to a subject in a section."""
        section = self.section_repo.get_by_id(dto.section_id)
        if not section:
            raise ValueError(f"Section {dto.section_id} not found")

        subject = self.subject_repo.get_by_id(dto.subject_id)
        if not subject:
            raise ValueError(f"Subject {dto.subject_id} not found")

        return self.assignment_repo.create(
            client_id, institution_id, academic_year_id,
            dto.teacher_id, dto.section_id, dto.subject_id,
        )

    def list_teacher_assignments(
        self,
        section_id: uuid.UUID | None = None,
        teacher_id: uuid.UUID | None = None,
        academic_year_id: uuid.UUID | None = None,
    ) -> Sequence[TeacherAssignment]:
        if section_id:
            return self.assignment_repo.list_by_section(section_id)
        if teacher_id:
            return self.assignment_repo.list_by_teacher(teacher_id, academic_year_id)
        if academic_year_id:
            return self.assignment_repo.list_by_academic_year(academic_year_id)
        return []

    def remove_teacher_assignment(self, assignment_id: uuid.UUID) -> TeacherAssignment:
        assignment = self.assignment_repo.get_by_id(assignment_id)
        if not assignment:
            raise ValueError(f"TeacherAssignment {assignment_id} not found")
        return self.assignment_repo.deactivate(assignment)
