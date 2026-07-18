"""Fees module — repositories (D3, D4, D5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from kernel.repo_base import TenantAwareRepositoryBase
from kernel.tenant_context import TenantContext
from business.fees.models.fee_models import FeeType, FeeAssignment, Payment
from business.fees.services.dtos import (
    FeeTypeCreateDTO, FeeTypeDTO, FeeTypeUpdateDTO,
    FeeAssignmentCreateDTO, FeeAssignmentDTO, FeeAssignmentUpdateDTO,
    PaymentCreateDTO, PaymentDTO,
)


class FeeTypeRepository(TenantAwareRepositoryBase[FeeType]):

    def __init__(self):
        super().__init__(FeeType)

    def _to_dto(self, obj: FeeType) -> FeeTypeDTO:
        return FeeTypeDTO(
            id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
            name=obj.name, description=obj.description,
            default_amount=obj.default_amount, is_active=obj.is_active,
            created_at=obj.created_at,
        )

    def create(self, session: Session, ctx: TenantContext, dto: FeeTypeCreateDTO) -> FeeTypeDTO:
        obj = FeeType(
            client_id=ctx.client_id, institution_id=dto.institution_id,
            name=dto.name, description=dto.description, default_amount=dto.default_amount,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def list_active(self, session: Session, ctx: TenantContext, institution_id: uuid.UUID | None = None) -> list[FeeTypeDTO]:
        stmt = select(FeeType).where(FeeType.is_active == True)
        stmt = self._apply_tenant_filter(stmt, ctx)
        if institution_id:
            stmt = stmt.where(FeeType.institution_id == institution_id)
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def update(self, session: Session, ctx: TenantContext, fee_type_id: uuid.UUID, dto: FeeTypeUpdateDTO) -> FeeTypeDTO:
        obj = session.get(FeeType, fee_type_id)
        if not obj:
            raise ValueError("Fee type not found")
        data = dto.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)


class FeeAssignmentRepository(TenantAwareRepositoryBase[FeeAssignment]):

    def __init__(self):
        super().__init__(FeeAssignment)

    def _to_dto(self, obj: FeeAssignment) -> FeeAssignmentDTO:
        return FeeAssignmentDTO(
            id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
            user_id=obj.user_id, fee_type_id=obj.fee_type_id,
            amount=obj.amount, due_date=obj.due_date, academic_term=obj.academic_term,
            status=obj.status, assigned_by=obj.assigned_by, notes=obj.notes,
            created_at=obj.created_at, total_paid=Decimal("0.00"),
        )

    def create(self, session: Session, ctx: TenantContext, user_id: uuid.UUID,
               fee_type_id: uuid.UUID, institution_id: uuid.UUID,
               amount: Decimal, due_date: date, academic_term: str | None,
               notes: str | None) -> FeeAssignmentDTO:
        obj = FeeAssignment(
            client_id=ctx.client_id, institution_id=institution_id,
            user_id=user_id, fee_type_id=fee_type_id,
            amount=amount, due_date=due_date, academic_term=academic_term,
            status="pending", assigned_by=uuid.UUID(ctx.user_id) if ctx.user_id else None,
            notes=notes,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def list_with_filters(self, session: Session, ctx: TenantContext,
                          user_id: uuid.UUID | None = None, status: str | None = None,
                          overdue: bool = False) -> list[FeeAssignmentDTO]:
        stmt = select(
            FeeAssignment, func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
        ).outerjoin(Payment).group_by(FeeAssignment.id)
        stmt = self._apply_tenant_filter(stmt, ctx)

        if user_id:
            stmt = stmt.where(FeeAssignment.user_id == user_id)
        if status:
            stmt = stmt.where(FeeAssignment.status == status)
        if overdue:
            stmt = stmt.where(
                FeeAssignment.due_date < date.today(),
                FeeAssignment.status.in_(["pending", "partial"]),
            )
        stmt = stmt.order_by(FeeAssignment.due_date.desc())

        rows = session.execute(stmt).all()
        result = []
        for obj, total_paid in rows:
            dto = self._to_dto(obj)
            dto.total_paid = Decimal(str(total_paid)) if total_paid else Decimal("0.00")
            result.append(dto)
        return result

    def update(self, session: Session, ctx: TenantContext, assignment_id: uuid.UUID,
               dto: FeeAssignmentUpdateDTO) -> FeeAssignmentDTO:
        obj = session.get(FeeAssignment, assignment_id)
        if not obj:
            raise ValueError("Fee assignment not found")
        if obj.status in ("paid", "waived"):
            raise ValueError(f"Cannot update a {obj.status} fee assignment")
        data = dto.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(obj, key, value)
        session.flush()
        return self._to_dto(obj)

    def waive(self, session: Session, ctx: TenantContext, assignment_id: uuid.UUID) -> FeeAssignmentDTO:
        obj = session.get(FeeAssignment, assignment_id)
        if not obj:
            raise ValueError("Fee assignment not found")
        obj.status = "waived"
        session.flush()
        return self._to_dto(obj)


class PaymentRepository(TenantAwareRepositoryBase[Payment]):

    def __init__(self):
        super().__init__(Payment)

    def _to_dto(self, obj: Payment) -> PaymentDTO:
        return PaymentDTO(
            id=obj.id, client_id=obj.client_id, institution_id=obj.institution_id,
            fee_assignment_id=obj.fee_assignment_id, amount=obj.amount,
            payment_date=obj.payment_date, payment_method=obj.payment_method,
            receipt_number=obj.receipt_number, reference_number=obj.reference_number,
            recorded_by=obj.recorded_by, notes=obj.notes, created_at=obj.created_at,
        )

    def create(self, session: Session, ctx: TenantContext, institution_id: uuid.UUID,
               dto: PaymentCreateDTO, receipt_number: str) -> PaymentDTO:
        obj = Payment(
            client_id=ctx.client_id, institution_id=institution_id,
            fee_assignment_id=dto.fee_assignment_id, amount=dto.amount,
            payment_date=dto.payment_date or date.today(),
            payment_method=dto.payment_method,
            receipt_number=receipt_number,
            reference_number=dto.reference_number,
            recorded_by=uuid.UUID(ctx.user_id) if ctx.user_id else None,
            notes=dto.notes,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def list_with_filters(self, session: Session, ctx: TenantContext,
                          fee_assignment_id: uuid.UUID | None = None,
                          user_id: uuid.UUID | None = None) -> list[PaymentDTO]:
        stmt = select(Payment)
        if user_id:
            stmt = stmt.join(FeeAssignment).where(FeeAssignment.user_id == user_id)
        stmt = self._apply_tenant_filter(stmt, ctx)
        if fee_assignment_id:
            stmt = stmt.where(Payment.fee_assignment_id == fee_assignment_id)
        stmt = stmt.order_by(Payment.payment_date.desc())
        result = session.execute(stmt).scalars().all()
        return [self._to_dto(obj) for obj in result]

    def get_total_payments(self, session: Session, assignment_id: uuid.UUID) -> Decimal:
        result = session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.fee_assignment_id == assignment_id)
        ).scalar()
        return Decimal(str(result)) if result else Decimal("0.00")

    def get_next_receipt_number(self, session: Session, institution_id: uuid.UUID) -> str:
        result = session.execute(
            select(Payment.receipt_number)
            .where(Payment.institution_id == institution_id, Payment.receipt_number.isnot(None))
            .order_by(Payment.receipt_number.desc())
            .limit(1)
            .with_for_update()
        ).scalars().first()

        # Extract short institution code from UUID
        inst_code = str(institution_id).replace("-", "")[:6].upper()

        if result and result.startswith(f"REC-{inst_code}-"):
            try:
                last_num = int(result.split("-")[-1]) + 1
            except ValueError:
                last_num = 1
        else:
            last_num = 1
        return f"REC-{inst_code}-{last_num:06d}"
