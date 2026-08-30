"""Employee DTOs — request/response models (D11)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmployeeCreateRequest(BaseModel):
    person_id: uuid.UUID
    joining_date: date | None = None
    employment_type: Literal["FULL_TIME", "PART_TIME", "CONTRACT", "TEMPORARY", "INTERN", "CONSULTANT"]
    department: str | None = Field(None, max_length=100)
    designation: str | None = Field(None, max_length=100)


class EmployeeUpdateRequest(BaseModel):
    joining_date: date | None = None
    employment_type: Literal["FULL_TIME", "PART_TIME", "CONTRACT", "TEMPORARY", "INTERN", "CONSULTANT"] | None = None
    department: str | None = Field(None, max_length=100)
    designation: str | None = Field(None, max_length=100)


class TerminateRequest(BaseModel):
    terminal_status: Literal["resigned", "terminated", "retired"]


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    person_id: uuid.UUID
    employee_no: str
    joining_date: date | None
    employment_type: str
    employment_status: str
    department: str | None
    designation: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    offset: int
    limit: int
