"""Fees module — ORM models (D3, D4, D5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from kernel.db import Base


class FeeType(Base):
    __tablename__ = "fee_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    default_amount = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FeeAssignment(Base):
    __tablename__ = "fee_assignment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False)
    fee_type_id = Column(UUID(as_uuid=True), ForeignKey("fee_type.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    academic_term = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    fee_assignment_id = Column(UUID(as_uuid=True), ForeignKey("fee_assignment.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    payment_method = Column(Text, nullable=False)
    receipt_number = Column(Text, nullable=True)
    reference_number = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
