"""Homework module — DTOs."""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class HomeworkCreateDTO(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    section: Optional[str] = None
    due_date: date
    max_score: Optional[int] = None


class HomeworkUpdateDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    section: Optional[str] = None
    due_date: Optional[date] = None
    max_score: Optional[int] = None
    status: Optional[str] = None


class HomeworkDTO(BaseModel):
    id: uuid.UUID; client_id: uuid.UUID; institution_id: uuid.UUID
    title: str; description: Optional[str] = None
    subject: Optional[str] = None; grade_level: Optional[str] = None; section: Optional[str] = None
    due_date: date; max_score: Optional[int] = None; status: str
    assigned_by: Optional[uuid.UUID] = None; created_at: datetime
    submission_count: int = 0
    model_config = {"from_attributes": True}


class SubmissionCreateDTO(BaseModel):
    homework_id: uuid.UUID
    content: str = Field(..., min_length=1)


class SubmissionDTO(BaseModel):
    id: uuid.UUID; client_id: uuid.UUID; institution_id: uuid.UUID
    homework_id: uuid.UUID; student_id: uuid.UUID
    content: Optional[str] = None; status: str
    submitted_at: datetime; created_at: datetime
    student_name: Optional[str] = None
    model_config = {"from_attributes": True}


class GradeCreateDTO(BaseModel):
    score: int = Field(..., ge=0)
    feedback: Optional[str] = None


class GradeUpdateDTO(BaseModel):
    score: Optional[int] = Field(None, ge=0)
    feedback: Optional[str] = None


class GradeDTO(BaseModel):
    id: uuid.UUID; client_id: uuid.UUID; institution_id: uuid.UUID
    submission_id: uuid.UUID; score: int; max_score: Optional[int] = None
    feedback: Optional[str] = None; graded_by: Optional[uuid.UUID] = None
    graded_at: datetime; created_at: datetime
    model_config = {"from_attributes": True}
