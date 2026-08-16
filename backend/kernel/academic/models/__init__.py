"""C-05 Academic Structure — models package."""

from kernel.academic.models.academic_year import AcademicYear
from kernel.academic.models.term import Term
from kernel.academic.models.grade_level import GradeLevel
from kernel.academic.models.class_entity import ClassEntity
from kernel.academic.models.section import Section
from kernel.academic.models.subject import Subject
from kernel.academic.models.subject_group import SubjectGroup, SubjectGroupMember
from kernel.academic.models.teacher_assignment import TeacherAssignment
from kernel.academic.models.student_enrollment import StudentEnrollment

__all__ = [
    "AcademicYear",
    "Term",
    "GradeLevel",
    "ClassEntity",
    "Section",
    "Subject",
    "SubjectGroup",
    "SubjectGroupMember",
    "TeacherAssignment",
    "StudentEnrollment",
]
