"""C-05 Academic Structure — DTOs (T23)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ============================================================
# AcademicYear DTOs
# ============================================================

class AcademicYearCreateDTO(BaseModel):
    name: str
    start_date: date
    end_date: date
    clone_from: uuid.UUID | None = None  # If None, clone from latest closed year or use template


class AcademicYearDTO(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AcademicYearTransitionDTO(BaseModel):
    new_state: str  # active | closed
    reason: str | None = None


# ============================================================
# Term DTOs
# ============================================================

class TermDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    sort_order: int

    class Config:
        from_attributes = True


# ============================================================
# GradeLevel DTOs
# ============================================================

class GradeLevelDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    sort_order: int

    class Config:
        from_attributes = True


# ============================================================
# Class DTOs
# ============================================================

class ClassDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    grade_level_id: uuid.UUID
    name: str
    sort_order: int

    class Config:
        from_attributes = True


# ============================================================
# Section DTOs
# ============================================================

class SectionDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    class_id: uuid.UUID
    name: str
    homeroom_teacher_id: uuid.UUID | None
    sort_order: int

    class Config:
        from_attributes = True


class SectionUpdateDTO(BaseModel):
    homeroom_teacher_id: uuid.UUID | None = None


# ============================================================
# Subject DTOs
# ============================================================

class SubjectDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    code: str | None
    sort_order: int

    class Config:
        from_attributes = True


class SubjectGroupDTO(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


# ============================================================
# Enrollment DTOs
# ============================================================

class StudentEnrollmentCreateDTO(BaseModel):
    student_id: uuid.UUID
    section_id: uuid.UUID


class StudentEnrollmentDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    student_id: uuid.UUID
    section_id: uuid.UUID
    enrolled_at: datetime
    status: str

    class Config:
        from_attributes = True


# ============================================================
# TeacherAssignment DTOs
# ============================================================

class TeacherAssignmentCreateDTO(BaseModel):
    teacher_id: uuid.UUID
    section_id: uuid.UUID
    subject_id: uuid.UUID


class TeacherAssignmentDTO(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    teacher_id: uuid.UUID
    section_id: uuid.UUID
    subject_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True


# ============================================================
# Structure DTOs (for full tree view)
# ============================================================

class AcademicStructureDTO(BaseModel):
    """Full academic structure for an AcademicYear."""
    academic_year: AcademicYearDTO
    terms: list[TermDTO]
    grade_levels: list[GradeLevelDTO]
    classes: list[ClassDTO]
    sections: list[SectionDTO]
    subjects: list[SubjectDTO]
