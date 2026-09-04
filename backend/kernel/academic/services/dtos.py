"""C-05 Academic Structure — DTOs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# AcademicYear DTOs
# ============================================================

class AcademicYearCreateDTO(BaseModel):
    name: str = Field(..., description="Academic year name, e.g. '2027-28'")
    start_date: date = Field(..., description="First day of the academic year")
    end_date: date = Field(..., description="Last day of the academic year")


class AcademicYearDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the academic year")
    client_id: uuid.UUID = Field(..., description="Client (tenant) this academic year belongs to")
    institution_id: uuid.UUID = Field(..., description="Institution this academic year belongs to")
    name: str = Field(..., description="Academic year name, e.g. '2027-28'")
    start_date: date = Field(..., description="First day of the academic year")
    end_date: date = Field(..., description="Last day of the academic year")
    status: str = Field(..., description="Lifecycle status: planning | active | closed | cancelled")
    closed_at: datetime | None = Field(None, description="Actual closure timestamp for early closure")
    created_at: datetime = Field(..., description="Timestamp when the academic year was created")
    updated_at: datetime = Field(..., description="Timestamp when the academic year was last updated")

    class Config:
        from_attributes = True


class AcademicYearTransitionDTO(BaseModel):
    new_state: str = Field(..., description="Target lifecycle state: active | closed | cancelled")
    reason: str | None = Field(None, description="Optional reason for the transition")


# ============================================================
# Term DTOs
# ============================================================

class TermCreateDTO(BaseModel):
    name: str = Field(..., description="Term name, e.g. 'Term 1'")
    start_date: date = Field(..., description="First day of the term")
    end_date: date = Field(..., description="Last day of the term")
    sort_order: int = Field(0, description="Ordering of the term within its academic year")


class TermDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the term")
    academic_year_id: uuid.UUID = Field(..., description="Academic year this term belongs to")
    name: str = Field(..., description="Term name, e.g. 'Term 1'")
    start_date: date = Field(..., description="First day of the term")
    end_date: date = Field(..., description="Last day of the term")
    sort_order: int = Field(..., description="Ordering of the term within its academic year")
    status: str = Field(..., description="Computed status: planned | active | completed")

    class Config:
        from_attributes = True


# ============================================================
# GradeLevel DTOs
# ============================================================

class GradeLevelCreateDTO(BaseModel):
    name: str = Field(..., description="Grade level name, e.g. 'Grade 10'")
    org_unit_id: uuid.UUID | None = Field(None, description="Optional OrgUnit association")
    sort_order: int = Field(0, description="Ordering of the grade level")


class GradeLevelDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the grade level")
    institution_id: uuid.UUID = Field(..., description="Institution this grade level belongs to")
    org_unit_id: uuid.UUID | None = Field(None, description="OrgUnit association")
    name: str = Field(..., description="Grade level name, e.g. 'Grade 10'")
    sort_order: int = Field(..., description="Ordering of the grade level")

    class Config:
        from_attributes = True


# ============================================================
# Class DTOs
# ============================================================

class ClassCreateDTO(BaseModel):
    grade_level_id: uuid.UUID = Field(..., description="Grade level this class belongs to")
    name: str = Field(..., description="Class name, e.g. '11'")
    sort_order: int = Field(0, description="Ordering of the class")


class ClassDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the class")
    institution_id: uuid.UUID = Field(..., description="Institution this class belongs to")
    grade_level_id: uuid.UUID = Field(..., description="Grade level this class belongs to")
    name: str = Field(..., description="Class name, e.g. '11'")
    sort_order: int = Field(..., description="Ordering of the class")

    class Config:
        from_attributes = True


# ============================================================
# ClassAcademicYear DTOs
# ============================================================

class ClassAcademicYearDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    class_id: uuid.UUID = Field(..., description="Class reference")
    academic_year_id: uuid.UUID = Field(..., description="Academic year reference")
    offered: bool = Field(..., description="Whether the class is offered this year")

    class Config:
        from_attributes = True


# ============================================================
# Section DTOs
# ============================================================

class SectionCreateDTO(BaseModel):
    name: str = Field(..., description="Section name, e.g. 'A'")
    sort_order: int = Field(0, description="Ordering of the section")


class SectionDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the section")
    class_academic_year_id: uuid.UUID = Field(..., description="ClassAcademicYear this section belongs to")
    name: str = Field(..., description="Section name, e.g. 'A'")
    sort_order: int = Field(..., description="Ordering of the section")

    class Config:
        from_attributes = True


# ============================================================
# Curriculum DTOs
# ============================================================

class CurriculumCreateDTO(BaseModel):
    grade_level_id: uuid.UUID = Field(..., description="Grade level this curriculum belongs to")
    name: str = Field(..., description="Curriculum name, e.g. 'Grade 11 Curriculum'")


class CurriculumDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    grade_level_id: uuid.UUID = Field(..., description="Grade level reference")
    name: str = Field(..., description="Curriculum name")

    class Config:
        from_attributes = True


# ============================================================
# CurriculumVersion DTOs
# ============================================================

class CurriculumVersionCreateDTO(BaseModel):
    name: str = Field(..., description="Version name, e.g. 'V1'")


class CurriculumVersionDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    curriculum_id: uuid.UUID = Field(..., description="Curriculum reference")
    version_number: int = Field(..., description="Version number")
    name: str = Field(..., description="Version name, e.g. 'V1'")

    class Config:
        from_attributes = True


# ============================================================
# Subject DTOs
# ============================================================

class SubjectCreateDTO(BaseModel):
    name: str = Field(..., description="Subject name, e.g. 'Mathematics'")
    code: str | None = Field(None, description="Optional subject code, e.g. 'MATH101'")
    sort_order: int = Field(0, description="Ordering of the subject")


class SubjectDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    curriculum_version_id: uuid.UUID = Field(..., description="CurriculumVersion reference")
    name: str = Field(..., description="Subject name, e.g. 'Mathematics'")
    code: str | None = Field(None, description="Optional subject code")
    sort_order: int = Field(..., description="Ordering of the subject")

    class Config:
        from_attributes = True


# ============================================================
# SectionSubject DTOs
# ============================================================

class SectionSubjectCreateDTO(BaseModel):
    subject_id: uuid.UUID = Field(..., description="Subject to assign to the section")


class SectionSubjectDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    section_id: uuid.UUID = Field(..., description="Section reference")
    subject_id: uuid.UUID = Field(..., description="Subject reference")
    is_active: bool = Field(..., description="Whether the subject is active for this section")
    created_at: datetime = Field(..., description="When the assignment was created")

    class Config:
        from_attributes = True


# ============================================================
# GradeAcademicYearCurriculum DTOs
# ============================================================

class GradeAcademicYearCurriculumAssignDTO(BaseModel):
    curriculum_version_id: uuid.UUID = Field(..., description="CurriculumVersion to assign")


class GradeAcademicYearCurriculumDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier")
    grade_level_id: uuid.UUID = Field(..., description="Grade level reference")
    academic_year_id: uuid.UUID = Field(..., description="Academic year reference")
    curriculum_version_id: uuid.UUID = Field(..., description="Assigned CurriculumVersion")

    class Config:
        from_attributes = True
