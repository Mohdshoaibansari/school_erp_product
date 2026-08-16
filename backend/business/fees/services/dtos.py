"""Fees module — DTOs (D4, D5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---- FeeType ----

class FeeTypeCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, description="Fee type name")
    description: Optional[str] = Field(None, description="Optional description of the fee type")
    default_amount: Decimal = Field(..., description="Default amount for this fee type")
    institution_id: uuid.UUID = Field(..., description="Institution this fee type belongs to")


class FeeTypeUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, description="Updated fee type name")
    description: Optional[str] = Field(None, description="Updated fee type description")
    default_amount: Optional[Decimal] = Field(None, description="Updated default amount")
    is_active: Optional[bool] = Field(None, description="Whether the fee type is active")


class FeeTypeDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Fee type ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    name: str = Field(..., description="Fee type name")
    description: Optional[str] = Field(None, description="Fee type description")
    default_amount: Decimal = Field(..., description="Default amount for this fee type")
    is_active: bool = Field(..., description="Whether the fee type is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


# ---- FeeAssignment ----

class FeeAssignmentCreateDTO(BaseModel):
    fee_type_id: uuid.UUID = Field(..., description="Fee type being assigned")
    amount: Decimal = Field(..., description="Amount to charge for this assignment")
    due_date: date = Field(..., description="Due date for the fee payment")
    term_id: Optional[uuid.UUID] = Field(None, description="Academic term this assignment applies to (C-05)")
    user_ids: list[uuid.UUID] = Field(..., description="Students the fee is assigned to")
    institution_id: Optional[uuid.UUID] = Field(None, description="Target institution (required for Client Director who has no context institution)")
    notes: Optional[str] = Field(None, description="Optional notes on the assignment")


class FeeAssignmentUpdateDTO(BaseModel):
    amount: Optional[Decimal] = Field(None, description="Updated amount")
    due_date: Optional[date] = Field(None, description="Updated due date")
    term_id: Optional[uuid.UUID] = Field(None, description="Updated academic term reference")
    notes: Optional[str] = Field(None, description="Updated notes")
    status: Optional[str] = Field(None, description="Updated assignment status (pending/paid/waived)")


class WaiveDTO(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason for waiving the fee")


class FeeAssignmentDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Fee assignment ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    user_id: uuid.UUID = Field(..., description="Student the fee is assigned to")
    fee_type_id: uuid.UUID = Field(..., description="Assigned fee type")
    amount: Decimal = Field(..., description="Assigned amount")
    due_date: date = Field(..., description="Due date")
    term_id: Optional[uuid.UUID] = Field(None, description="Academic term reference (C-05)")
    status: str = Field(..., description="Assignment status (pending/paid/waived)")
    assigned_by: Optional[uuid.UUID] = Field(None, description="User who created the assignment")
    notes: Optional[str] = Field(None, description="Assignment notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_paid: Decimal = Field(Decimal("0.00"), description="Total amount paid so far")

    model_config = {"from_attributes": True}


# ---- Payment ----

class PaymentCreateDTO(BaseModel):
    fee_assignment_id: uuid.UUID = Field(..., description="Fee assignment being paid")
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be positive)")
    payment_method: str = Field(..., min_length=1, description="Payment method (cash/upi/bank/etc.)")
    payment_date: Optional[date] = Field(None, description="Date payment was made (defaults to today)")
    reference_number: Optional[str] = Field(None, description="External payment reference/transaction number")
    notes: Optional[str] = Field(None, description="Optional payment notes")


class PaymentDTO(BaseModel):
    id: uuid.UUID = Field(..., description="Payment ID")
    client_id: uuid.UUID = Field(..., description="Owning client ID")
    institution_id: uuid.UUID = Field(..., description="Owning institution ID")
    fee_assignment_id: uuid.UUID = Field(..., description="Fee assignment this payment settles")
    amount: Decimal = Field(..., description="Payment amount")
    payment_date: date = Field(..., description="Date payment was made")
    payment_method: str = Field(..., description="Payment method used")
    receipt_number: Optional[str] = Field(None, description="System-generated receipt number")
    reference_number: Optional[str] = Field(None, description="External payment reference/transaction number")
    recorded_by: Optional[uuid.UUID] = Field(None, description="User who recorded the payment")
    notes: Optional[str] = Field(None, description="Payment notes")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}
