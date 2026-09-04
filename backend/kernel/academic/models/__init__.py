"""C-05 Academic Structure — models package."""

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

__all__ = [
    "AcademicYear",
    "Term",
    "GradeLevel",
    "Class",
    "ClassAcademicYear",
    "Section",
    "Curriculum",
    "CurriculumVersion",
    "Subject",
    "SectionSubject",
    "GradeAcademicYearCurriculum",
]
