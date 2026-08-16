"""C-05 Academic Structure — DTOs (T23)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# AcademicYear DTOs
# ============================================================

class AcademicYearCreateDTO(BaseModel):
    name: str = Field(..., description="Academic year name, e.g. '2025-26'")
    start_date: date = Field(..., description="First day of the academic year")
    end_date: date = Field(..., description="Last day of the academic year")
    clone_from: uuid.UUID | None = Field(None, description="Source year to clone structure from; defaults to latest closed year or template")


class AcademicYearDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the academic year")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this academic year belongs to")
    institution_id: uuid.UUID = Field(..., description="Institution this academic year belongs to")
    name: str = Field(..., description="Academic year name, e.g. '2025-26'")
    start_date: date = Field(..., description="First day of the academic year")
    end_date: date = Field(..., description="Last day of the academic year")
    status: str = Field(..., description="Lifecycle status: planning | active | closed")
    created_at: datetime = Field(..., description="Timestamp when the academic year was created")
    updated_at: datetime = Field(..., description="Timestamp when the academic year was last updated")

    class Config:
        from_attributes = True


class AcademicYearTransitionDTO(BaseModel):
    new_state: str = Field(..., description="Target lifecycle state: active | closed")
    reason: str | None = Field(None, description="Optional reason for the transition")


# ============================================================
# Term DTOs
# ============================================================

class TermDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the term")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this term belongs to")
    name: str = Field(..., description="Term name, e.g. 'Term 1'")
    start_date: date = Field(..., description="First day of the term")
    end_date: date = Field(..., description="Last day of the term")
    sort_order: int = Field(..., description="Ordering of the term within its academic year")

    class Config:
        from_attributes = True


# ============================================================
# GradeLevel DTOs
# ============================================================

class GradeLevelDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the grade level")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this grade level belongs to")
    name: str = Field(..., description="Grade level name, e.g. 'Grade 10'")
    sort_order: int = Field(..., description="Ordering of the grade level within its academic year")

    class Config:
        from_attributes = True


# ============================================================
# Class DTOs
# ============================================================

class ClassDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the class")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this class belongs to")
    grade_level_id: uuid.UUID = Field(..., description="Grade level this class belongs to")
    name: str = Field(..., description="Class name, e.g. '10A'")
    sort_order: int = Field(..., description="Ordering of the class within its grade level")

    class Config:
        from_attributes = True


# ============================================================
# Section DTOs
# ============================================================

class SectionDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the section")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this section belongs to")
    class_id: uuid.UUID = Field(..., description="Class this section belongs to")
    name: str = Field(..., description="Section name, e.g. 'A'")
    homeroom_teacher_id: uuid.UUID | None = Field(None, description="Optional homeroom teacher (app_user id) for this section")
    sort_order: int = Field(..., description="Ordering of the section within its class")

    class Config:
        from_attributes = True


class SectionUpdateDTO(BaseModel):
    homeroom_teacher_id: uuid.UUID | None = Field(None, description="Homeroom teacher (app_user id) to assign to the section, or null to clear")


# ============================================================
# Subject DTOs
# ============================================================

class SubjectDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the subject")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this subject belongs to")
    name: str = Field(..., description="Subject name, e.g. 'Mathematics'")
    code: str | None = Field(None, description="Optional subject code, e.g. 'MATH101'")
    sort_order: int = Field(..., description="Ordering of the subject within its academic year")

    class Config:
        from_attributes = True


class SubjectGroupDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the subject group")
    name: str = Field(..., description="Subject group name, e.g. 'Science Group'")

    class Config:
        from_attributes = True


# ============================================================
# Enrollment DTOs
# ============================================================

class StudentEnrollmentCreateDTO(BaseModel):
    student_id: uuid.UUID = Field(..., description="Student (app_user id) to enroll")
    section_id: uuid.UUID = Field(..., description="Section the student is enrolled into")


class StudentEnrollmentDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the enrollment")
    academic_year_id: uuid.UUID = Field(..., description="Academic year of the enrollment")
    student_id: uuid.UUID = Field(..., description="Enrolled student (app_user id)")
    section_id: uuid.UUID = Field(..., description="Section the student is enrolled into")
    enrolled_at: datetime = Field(..., description="Timestamp when the student was enrolled")
    status: str = Field(..., description="Enrollment status: active | transferred | withdrawn | archived")

    class Config:
        from_attributes = True


# ============================================================
# TeacherAssignment DTOs
# ============================================================

class TeacherAssignmentCreateDTO(BaseModel):
    teacher_id: uuid.UUID = Field(..., description="Teacher (app_user id) being assigned")
    section_id: uuid.UUID = Field(..., description="Section the teacher is assigned to")
    subject_id: uuid.UUID = Field(..., description="Subject the teacher is assigned to teach")


class TeacherAssignmentDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the teacher assignment")
    academic_year_id: uuid.UUID = Field(..., description="Academic year of the assignment")
    teacher_id: uuid.UUID = Field(..., description="Assigned teacher (app_user id)")
    section_id: uuid.UUID = Field(..., description="Section the teacher is assigned to")
    subject_id: uuid.UUID = Field(..., description="Subject the teacher is assigned to teach")
    status: str = Field(..., description="Assignment status: active | inactive | archived")

    class Config:
        from_attributes = True


# ============================================================
# Structure DTOs (for full tree view)
# ============================================================

class AcademicStructureDTO(BaseModel):
    """Full academic structure for an AcademicYear."""
    academic_year: AcademicYearDTO = Field(..., description="The academic year itself")
    terms: list[TermDTO] = Field(..., description="Terms belonging to the academic year")
    grade_levels: list[GradeLevelDTO] = Field(..., description="Grade levels belonging to the academic year")
    classes: list[ClassDTO] = Field(..., description="Classes belonging to the academic year")
    sections: list[SectionDTO] = Field(..., description="Sections belonging to the academic year")
    subjects: list[SubjectDTO] = Field(..., description="Subjects belonging to the academic year")
