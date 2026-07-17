"""Fees module — DTOs (D4, D5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---- FeeType ----

class FeeTypeCreateDTO(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    default_amount: Decimal
    institution_id: uuid.UUID


class FeeTypeUpdateDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_amount: Optional[Decimal] = None
    is_active: Optional[bool] = None


class FeeTypeDTO(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    description: Optional[str] = None
    default_amount: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- FeeAssignment ----

class FeeAssignmentCreateDTO(BaseModel):
    fee_type_id: uuid.UUID
    amount: Decimal
    due_date: date
    academic_term: Optional[str] = None
    user_ids: list[uuid.UUID]
    notes: Optional[str] = None


class FeeAssignmentUpdateDTO(BaseModel):
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    academic_term: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class WaiveDTO(BaseModel):
    reason: str = Field(..., min_length=1)


class FeeAssignmentDTO(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    user_id: uuid.UUID
    fee_type_id: uuid.UUID
    amount: Decimal
    due_date: date
    academic_term: Optional[str] = None
    status: str
    assigned_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    total_paid: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}


# ---- Payment ----

class PaymentCreateDTO(BaseModel):
    fee_assignment_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1)
    payment_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentDTO(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    institution_id: uuid.UUID
    fee_assignment_id: uuid.UUID
    amount: Decimal
    payment_date: date
    payment_method: str
    receipt_number: Optional[str] = None
    reference_number: Optional[str] = None
    recorded_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
