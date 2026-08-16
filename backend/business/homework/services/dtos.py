"""Homework module — DTOs."""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class HomeworkCreateDTO(BaseModel):
    title: str = Field(..., min_length=1, description="Homework title")
    description: Optional[str] = Field(None, description="Detailed homework description")
    subject_id: Optional[uuid.UUID] = Field(None, description="Subject this homework belongs to (C-05)")
    grade_level_id: Optional[uuid.UUID] = Field(None, description="Grade level targeted (C-05)")
    section_id: Optional[uuid.UUID] = Field(None, description="Section targeted (C-05, implies academic year)")
    due_date: date = Field(..., description="Submission due date")
    max_score: Optional[int] = Field(None, description="Maximum possible score")


class HomeworkUpdateDTO(BaseModel):
    title: Optional[str] = Field(None, description="Updated homework title")
    description: Optional[str] = Field(None, description="Updated homework description")
    subject_id: Optional[uuid.UUID] = Field(None, description="Updated subject reference (C-05)")
    grade_level_id: Optional[uuid.UUID] = Field(None, description="Updated grade level reference (C-05)")
    section_id: Optional[uuid.UUID] = Field(None, description="Updated section reference (C-05)")
    due_date: Optional[date] = Field(None, description="Updated due date")
    max_score: Optional[int] = Field(None, description="Updated maximum score")
    status: Optional[str] = Field(None, description="Updated homework status (active/closed/archived)")


class HomeworkDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Homework ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    title: str = Field(..., description="Homework title")
    description: Optional[str] = Field(None, description="Homework description")
    subject_id: Optional[uuid.UUID] = Field(None, description="Subject reference (C-05)")
    grade_level_id: Optional[uuid.UUID] = Field(None, description="Grade level reference (C-05)")
    section_id: Optional[uuid.UUID] = Field(None, description="Section reference (C-05)")
    due_date: date = Field(..., description="Submission due date")
    max_score: Optional[int] = Field(None, description="Maximum possible score")
    status: str = Field(..., description="Homework status (active/closed/archived)")
    assigned_by: Optional[uuid.UUID] = Field(None, description="Teacher who assigned the homework")
    created_at: datetime = Field(..., description="Creation timestamp")
    submission_count: int = Field(0, description="Number of student submissions")

    model_config = {"from_attributes": True}


class SubmissionCreateDTO(BaseModel):
    homework_id: uuid.UUID = Field(..., description="Homework being submitted to")
    content: str = Field(..., min_length=1, description="Submission content/text")


class SubmissionDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Submission ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    homework_id: uuid.UUID = Field(..., description="Homework this submission belongs to")
    student_id: uuid.UUID = Field(..., description="Student who submitted")
    content: Optional[str] = Field(None, description="Submission content")
    status: str = Field(..., description="Submission status (submitted/late/graded)")
    submitted_at: datetime = Field(..., description="Submission timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    student_name: Optional[str] = Field(None, description="Student display name (joined for listing)")

    model_config = {"from_attributes": True}


class GradeCreateDTO(BaseModel):
    score: int = Field(..., ge=0, description="Score awarded (>= 0)")
    feedback: Optional[str] = Field(None, description="Teacher feedback on the submission")


class GradeUpdateDTO(BaseModel):
    score: Optional[int] = Field(None, ge=0, description="Updated score (>= 0)")
    feedback: Optional[str] = Field(None, description="Updated feedback")


class GradeDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Grade ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    submission_id: uuid.UUID = Field(..., description="Submission being graded")
    score: int = Field(..., description="Score awarded")
    max_score: Optional[int] = Field(None, description="Maximum possible score (from homework)")
    feedback: Optional[str] = Field(None, description="Teacher feedback")
    graded_by: Optional[uuid.UUID] = Field(None, description="Teacher who graded")
    graded_at: datetime = Field(..., description="Grading timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}
