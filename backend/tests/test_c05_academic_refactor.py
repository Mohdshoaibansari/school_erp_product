"""C-05 Academic Structure Refactor — Tests.

Tests for:
- AcademicYear lifecycle (planning → active → closed, cancelled)
- Term dynamic status
- ClassAcademicYear auto-creation
- SectionSubject validation against CurriculumVersion
- Section mutability rules
- CurriculumVersion immutability
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.term import Term
from kernel.academic.models.grade_level import GradeLevel
from kernel.academic.models.class_entity import Class
from kernel.academic.models.class_academic_year import ClassAcademicYear
from kernel.academic.models.section import Section
from kernel.academic.models.curriculum import Curriculum
from kernel.academic.models.curriculum_version import CurriculumVersion
from kernel.academic.models.subject import Subject
from kernel.academic.models.section_subject import SectionSubject
from kernel.academic.models.grade_academic_year_curriculum import GradeAcademicYearCurriculum

from kernel.academic.repos.academic_repo import AcademicYearRepo, TermRepo
from kernel.academic.repos.structure_repo import GradeLevelRepo, ClassRepo, SectionRepo
from kernel.academic.repos.class_academic_year_repo import ClassAcademicYearRepo
from kernel.academic.repos.curriculum_repo import CurriculumRepo
from kernel.academic.repos.curriculum_version_repo import CurriculumVersionRepo
from kernel.academic.repos.subject_repo import SubjectRepo
from kernel.academic.repos.section_subject_repo import SectionSubjectRepo
from kernel.academic.repos.grade_academic_year_curriculum_repo import GradeAcademicYearCurriculumRepo

from kernel.academic.services.lifecycle_service import LifecycleService
from kernel.academic.services.service import AcademicService
from kernel.academic.services.class_academic_year_service import ClassAcademicYearService
from kernel.academic.services.curriculum_service import CurriculumService
from kernel.academic.services.curriculum_version_service import CurriculumVersionService
from kernel.academic.services.section_subject_service import SectionSubjectService
from kernel.academic.services.grade_academic_year_curriculum_service import GradeAcademicYearCurriculumService


# ============================================================
# Test AcademicYear Lifecycle
# ============================================================

class TestAcademicYearLifecycle:
    """Tests for AcademicYear lifecycle transitions."""

    def test_planning_to_active(self, db: Session, test_client_id, test_institution_id):
        """Test planning → active transition."""
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "planning")

        svc = LifecycleService(db)
        result = svc.transition(year, "active")

        assert result.status == "active"

    def test_active_to_closed(self, db: Session, test_client_id, test_institution_id):
        """Test active → closed transition sets closed_at."""
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "active")

        svc = LifecycleService(db)
        result = svc.transition(year, "closed")

        assert result.status == "closed"
        assert result.closed_at is not None

    def test_planning_to_cancelled(self, db: Session, test_client_id, test_institution_id):
        """Test planning → cancelled transition."""
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "planning")

        svc = LifecycleService(db)
        result = svc.transition(year, "cancelled")

        assert result.status == "cancelled"

    def test_cannot_activate_with_existing_active(self, db: Session, test_client_id, test_institution_id):
        """Test that activating a year fails if another year is already active."""
        year_repo = AcademicYearRepo(db)
        svc = LifecycleService(db)

        # Create active year
        year1 = year_repo.create(test_client_id, test_institution_id, "2026-27", date(2026, 4, 1), date(2027, 3, 31), "active")

        # Create planning year
        year2 = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "planning")

        # Try to activate year2 - should fail
        with pytest.raises(ValueError, match="Cannot activate"):
            svc.transition(year2, "active")

    def test_invalid_transition_raises(self, db: Session, test_client_id, test_institution_id):
        """Test that invalid transitions raise ValueError."""
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "closed")

        svc = LifecycleService(db)
        with pytest.raises(ValueError, match="Invalid transition"):
            svc.transition(year, "active")

    def test_cancelled_is_terminal(self, db: Session, test_client_id, test_institution_id):
        """Test that cancelled is a terminal state."""
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "cancelled")

        svc = LifecycleService(db)
        with pytest.raises(ValueError, match="Invalid transition"):
            svc.transition(year, "active")


# ============================================================
# Test Term Dynamic Status
# ============================================================

class TestTermDynamicStatus:
    """Tests for Term status computation."""

    def test_planned_status(self, db: Session, test_client_id, test_institution_id):
        """Test term status is 'planned' before start_date."""
        term = Term(
            client_id=test_client_id,
            institution_id=test_institution_id,
            academic_year_id=uuid.uuid4(),
            name="Term 1",
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
            sort_order=1,
        )
        assert term.status == "planned"

    def test_active_status(self, db: Session, test_client_id, test_institution_id):
        """Test term status is 'active' between start_date and end_date."""
        term = Term(
            client_id=test_client_id,
            institution_id=test_institution_id,
            academic_year_id=uuid.uuid4(),
            name="Term 1",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=10),
            sort_order=1,
        )
        assert term.status == "active"

    def test_completed_status(self, db: Session, test_client_id, test_institution_id):
        """Test term status is 'completed' after end_date."""
        term = Term(
            client_id=test_client_id,
            institution_id=test_institution_id,
            academic_year_id=uuid.uuid4(),
            name="Term 1",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            sort_order=1,
        )
        assert term.status == "completed"


# ============================================================
# Test ClassAcademicYear Auto-Creation
# ============================================================

class TestClassAcademicYearAutoCreation:
    """Tests for ClassAcademicYear auto-creation."""

    def test_auto_create_on_academic_year_creation(self, db: Session, test_client_id, test_institution_id):
        """Test that creating an AcademicYear auto-creates ClassAcademicYear for all existing Classes."""
        # Create GradeLevel and Class
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)

        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        class1 = class_repo.create(test_client_id, test_institution_id, grade.id, "10")
        class2 = class_repo.create(test_client_id, test_institution_id, grade.id, "11")

        # Create AcademicYear
        svc = AcademicService(db)
        from kernel.academic.services.dtos import AcademicYearCreateDTO
        dto = AcademicYearCreateDTO(
            name="2027-28",
            start_date=date(2027, 4, 1),
            end_date=date(2028, 3, 31),
        )
        year = svc.create_academic_year(test_client_id, test_institution_id, dto)

        # Verify ClassAcademicYear created for each Class
        cay_repo = ClassAcademicYearRepo(db)
        cays = cay_repo.list_by_academic_year(year.id)
        assert len(cays) == 2

    def test_new_class_not_auto_added_to_existing_years(self, db: Session, test_client_id, test_institution_id):
        """Test that creating a new Class does not auto-add to existing Planning years."""
        # Create AcademicYear first
        year_repo = AcademicYearRepo(db)
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))

        # Create new Class after year creation
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        new_class = class_repo.create(test_client_id, test_institution_id, grade.id, "10")

        # Verify ClassAcademicYear NOT created for existing year
        cay_repo = ClassAcademicYearRepo(db)
        cay = cay_repo.get_by_class_and_year(new_class.id, year.id)
        assert cay is None


# ============================================================
# Test SectionSubject Validation
# ============================================================

class TestSectionSubjectValidation:
    """Tests for SectionSubject validation against CurriculumVersion."""

    def test_assign_subject_from_valid_curriculum_version(self, db: Session, test_client_id, test_institution_id):
        """Test assigning a Subject that belongs to the applicable CurriculumVersion."""
        # Create full hierarchy
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)
        cay_repo = ClassAcademicYearRepo(db)
        section_repo = SectionRepo(db)
        curriculum_repo = CurriculumRepo(db)
        cv_repo = CurriculumVersionRepo(db)
        subject_repo = SubjectRepo(db)
        gayc_repo = GradeAcademicYearCurriculumRepo(db)
        year_repo = AcademicYearRepo(db)

        # Create entities
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        cls = class_repo.create(test_client_id, test_institution_id, grade.id, "10")
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))
        cay = cay_repo.create(test_client_id, test_institution_id, cls.id, year.id)
        section = section_repo.create(test_client_id, test_institution_id, cay.id, "A")

        # Create curriculum and version
        curriculum = curriculum_repo.create(test_client_id, test_institution_id, grade.id, "Grade 10 Curriculum")
        cv = cv_repo.create(test_client_id, test_institution_id, curriculum.id, 1, "V1")

        # Create subject in curriculum version
        subject = subject_repo.create(test_client_id, test_institution_id, cv.id, "Mathematics")

        # Assign curriculum version to grade for year
        gayc_repo.create(test_client_id, test_institution_id, grade.id, year.id, cv.id)

        # Assign subject to section
        ss_svc = SectionSubjectService(db)
        ss = ss_svc.assign_subject_to_section(test_client_id, test_institution_id, section.id, subject.id)

        assert ss.is_active is True

    def test_reject_subject_from_wrong_curriculum_version(self, db: Session, test_client_id, test_institution_id):
        """Test that assigning a Subject from wrong CurriculumVersion raises ValueError."""
        # Create full hierarchy
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)
        cay_repo = ClassAcademicYearRepo(db)
        section_repo = SectionRepo(db)
        curriculum_repo = CurriculumRepo(db)
        cv_repo = CurriculumVersionRepo(db)
        subject_repo = SubjectRepo(db)
        gayc_repo = GradeAcademicYearCurriculumRepo(db)
        year_repo = AcademicYearRepo(db)

        # Create entities
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        cls = class_repo.create(test_client_id, test_institution_id, grade.id, "10")
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))
        cay = cay_repo.create(test_client_id, test_institution_id, cls.id, year.id)
        section = section_repo.create(test_client_id, test_institution_id, cay.id, "A")

        # Create two curriculum versions
        curriculum = curriculum_repo.create(test_client_id, test_institution_id, grade.id, "Grade 10 Curriculum")
        cv1 = cv_repo.create(test_client_id, test_institution_id, curriculum.id, 1, "V1")
        cv2 = cv_repo.create(test_client_id, test_institution_id, curriculum.id, 2, "V2")

        # Create subject in V2
        subject = subject_repo.create(test_client_id, test_institution_id, cv2.id, "Physics")

        # Assign V1 to grade for year
        gayc_repo.create(test_client_id, test_institution_id, grade.id, year.id, cv1.id)

        # Try to assign subject from V2 - should fail
        ss_svc = SectionSubjectService(db)
        with pytest.raises(ValueError, match="does not belong to the applicable CurriculumVersion"):
            ss_svc.assign_subject_to_section(test_client_id, test_institution_id, section.id, subject.id)


# ============================================================
# Test Section Mutability
# ============================================================

class TestSectionMutability:
    """Tests for Section mutability rules."""

    def test_section_can_be_created_during_planning(self, db: Session, test_client_id, test_institution_id):
        """Test that Sections can be created during Planning."""
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)
        cay_repo = ClassAcademicYearRepo(db)
        section_repo = SectionRepo(db)
        year_repo = AcademicYearRepo(db)

        # Create planning year
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        cls = class_repo.create(test_client_id, test_institution_id, grade.id, "10")
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31), "planning")
        cay = cay_repo.create(test_client_id, test_institution_id, cls.id, year.id)

        # Create section
        section = section_repo.create(test_client_id, test_institution_id, cay.id, "A")
        assert section.name == "A"


# ============================================================
# Test CurriculumVersion Immutability
# ============================================================

class TestCurriculumVersionImmutability:
    """Tests for CurriculumVersion immutability."""

    def test_curriculum_version_auto_increments(self, db: Session, test_client_id, test_institution_id):
        """Test that CurriculumVersion auto-increments version number."""
        grade_repo = GradeLevelRepo(db)
        curriculum_repo = CurriculumRepo(db)
        cv_repo = CurriculumVersionRepo(db)

        # Create curriculum
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        curriculum = curriculum_repo.create(test_client_id, test_institution_id, grade.id, "Grade 10 Curriculum")

        # Create versions
        cv_svc = CurriculumVersionService(db)
        v1 = cv_svc.create_curriculum_version(test_client_id, test_institution_id, curriculum.id, "V1")
        v2 = cv_svc.create_curriculum_version(test_client_id, test_institution_id, curriculum.id, "V2")

        assert v1.version_number == 1
        assert v2.version_number == 2


# ============================================================
# Test AcademicYear Overlap
# ============================================================

class TestAcademicYearOverlap:
    """Tests for AcademicYear date overlap validation."""

    def test_overlap_detection(self, db: Session, test_client_id, test_institution_id):
        """Test that overlapping AcademicYears are detected."""
        year_repo = AcademicYearRepo(db)

        # Create first year
        year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))

        # Check overlap with overlapping dates
        has_overlap = year_repo.check_overlap(test_institution_id, date(2027, 10, 1), date(2028, 9, 30))
        assert has_overlap is True

    def test_no_overlap_detection(self, db: Session, test_client_id, test_institution_id):
        """Test that non-overlapping AcademicYears are detected."""
        year_repo = AcademicYearRepo(db)

        # Create first year
        year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))

        # Check overlap with non-overlapping dates
        has_overlap = year_repo.check_overlap(test_institution_id, date(2028, 4, 1), date(2029, 3, 31))
        assert has_overlap is False


# ============================================================
# Test ClassAcademicYear Offered Flag
# ============================================================

class TestClassAcademicYearOffered:
    """Tests for ClassAcademicYear offered flag."""

    def test_cannot_set_offered_false_with_sections(self, db: Session, test_client_id, test_institution_id):
        """Test that setting offered=false fails if Sections exist."""
        grade_repo = GradeLevelRepo(db)
        class_repo = ClassRepo(db)
        cay_repo = ClassAcademicYearRepo(db)
        section_repo = SectionRepo(db)
        year_repo = AcademicYearRepo(db)

        # Create hierarchy
        grade = grade_repo.create(test_client_id, test_institution_id, "Grade 10")
        cls = class_repo.create(test_client_id, test_institution_id, grade.id, "10")
        year = year_repo.create(test_client_id, test_institution_id, "2027-28", date(2027, 4, 1), date(2028, 3, 31))
        cay = cay_repo.create(test_client_id, test_institution_id, cls.id, year.id)

        # Create section
        section_repo.create(test_client_id, test_institution_id, cay.id, "A")

        # Try to set offered=false - should fail
        cay_svc = ClassAcademicYearService(db)
        with pytest.raises(ValueError, match="Cannot set offered=false"):
            cay_svc.update_offered(cay.id, False)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def test_client_id():
    return uuid.uuid4()


@pytest.fixture
def test_institution_id():
    return uuid.uuid4()


@pytest.fixture
def db():
    """Mock DB session for unit tests."""
    from unittest.mock import MagicMock
    return MagicMock(spec=Session)
