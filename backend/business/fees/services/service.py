"""Fees module — service layer (D6, D10, D11, D12, D13, D17)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from kernel.audit import AuditEmitter
from business.fees.repos.fee_repos import FeeTypeRepository, FeeAssignmentRepository, PaymentRepository
from business.fees.services.dtos import (
    FeeTypeCreateDTO, FeeTypeDTO, FeeTypeUpdateDTO,
    FeeAssignmentCreateDTO, FeeAssignmentDTO, FeeAssignmentUpdateDTO,
    PaymentCreateDTO, PaymentDTO, WaiveDTO,
)


class FeesService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None,
                 audit_emitter: AuditEmitter | None = None):
        self._session_factory = session_factory
        self._audit = audit_emitter
        self._fee_type_repo = FeeTypeRepository()
        self._fee_assignment_repo = FeeAssignmentRepository()
        self._payment_repo = PaymentRepository()

    # ---- FeeType CRUD ----

    def create_fee_type(self, ctx: TenantContext, dto: FeeTypeCreateDTO) -> FeeTypeDTO:
        with self._session_factory() as session:
            result = self._fee_type_repo.create(session, ctx, dto)
            session.commit()
            if self._audit:
                self._audit.emit(action="fee_type_created", client_id=ctx.client_id, institution_id=ctx.institution_id,
                                 actor=ctx.user_id or "system",
                                 payload={"fee_type_id": str(result.id), "name": result.name,
                                  "amount": str(result.default_amount)})
            return result

    def list_fee_types(self, ctx: TenantContext, institution_id: uuid.UUID | None = None) -> list[FeeTypeDTO]:
        with self._session_factory() as session:
            return self._fee_type_repo.list_active(session, ctx, institution_id)

    def get_fee_type(self, ctx: TenantContext, fee_type_id: uuid.UUID) -> FeeTypeDTO | None:
        with self._session_factory() as session:
            return self._fee_type_repo.get(session, ctx, fee_type_id)

    def update_fee_type(self, ctx: TenantContext, fee_type_id: uuid.UUID, dto: FeeTypeUpdateDTO) -> FeeTypeDTO:
        with self._session_factory() as session:
            result = self._fee_type_repo.update(session, ctx, fee_type_id, dto)
            session.commit()
            if self._audit:
                self._audit.emit(action="fee_type_updated", client_id=ctx.client_id, institution_id=ctx.institution_id,
                                 actor=ctx.user_id or "system",
                                 payload={"fee_type_id": str(result.id)})
            return result

    def deactivate_fee_type(self, ctx: TenantContext, fee_type_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            self._fee_type_repo.update(session, ctx, fee_type_id, FeeTypeUpdateDTO(is_active=False))
            session.commit()

    # ---- FeeAssignment ----

    def create_fee_assignments(self, ctx: TenantContext, dto: FeeAssignmentCreateDTO) -> list[FeeAssignmentDTO]:
        with self._session_factory() as session:
            session.execute(__import__("sqlalchemy").text(
                "SELECT 1 FROM app_user WHERE id = ANY(:ids) AND user_category_id NOT IN "
                "(SELECT id FROM user_category WHERE name = 'Learner')"
            ), {"ids": dto.user_ids})
            # Simple validation: check all user_ids belong to Learner category
            from sqlalchemy import text as sa_text
            bad_users = session.execute(sa_text(
                "SELECT u.id FROM app_user u "
                "JOIN user_category uc ON u.user_category_id = uc.id "
                "WHERE u.id = ANY(:ids) AND uc.name != 'Learner'"
            ), {"ids": dto.user_ids}).fetchall()
            if bad_users:
                raise ValueError(f"Fee can only be assigned to students (Learner category). "
                                 f"Invalid user IDs: {[str(r[0]) for r in bad_users]}")

            results = []
            for user_id in dto.user_ids:
                assignment = self._fee_assignment_repo.create(
                    session, ctx, user_id, dto.fee_type_id,
                    ctx.institution_id, dto.amount, dto.due_date,
                    dto.academic_term, dto.notes,
                )
                results.append(assignment)
            session.commit()

            if self._audit:
                for r in results:
                    self._audit.emit(action="fee_assigned", client_id=ctx.client_id, institution_id=ctx.institution_id,
                                     actor=ctx.user_id or "system",
                                     payload={"assignment_id": str(r.id), "user_id": str(r.user_id),
                                      "amount": str(r.amount), "due_date": str(r.due_date)})
            return results

    def list_fee_assignments(self, ctx: TenantContext, user_id: uuid.UUID | None = None,
                             status: str | None = None, overdue: bool = False) -> list[FeeAssignmentDTO]:
        self._enforce_ownership(ctx, user_id)
        with self._session_factory() as session:
            return self._fee_assignment_repo.list_with_filters(session, ctx, user_id, status, overdue)

    def get_fee_assignment(self, ctx: TenantContext, assignment_id: uuid.UUID) -> FeeAssignmentDTO | None:
        with self._session_factory() as session:
            return self._fee_assignment_repo.get(session, ctx, assignment_id)

    def update_fee_assignment(self, ctx: TenantContext, assignment_id: uuid.UUID,
                              dto: FeeAssignmentUpdateDTO) -> FeeAssignmentDTO:
        with self._session_factory() as session:
            result = self._fee_assignment_repo.update(session, ctx, assignment_id, dto)
            session.commit()
            return result

    def waive_fee_assignment(self, ctx: TenantContext, assignment_id: uuid.UUID, reason: str) -> FeeAssignmentDTO:
        with self._session_factory() as session:
            result = self._fee_assignment_repo.waive(session, ctx, assignment_id)
            session.commit()
            if self._audit:
                self._audit.emit(action="fee_waived", client_id=ctx.client_id, institution_id=ctx.institution_id,
                                 actor=ctx.user_id or "system",
                                 payload={"assignment_id": str(result.id), "user_id": str(result.user_id),
                                  "reason": reason})
            return result

    # ---- Payment ----

    def record_payment(self, ctx: TenantContext, dto: PaymentCreateDTO) -> PaymentDTO:
        with self._session_factory() as session:
            # Get assignment to find institution_id and update status
            assignment = self._fee_assignment_repo.get(session, ctx, dto.fee_assignment_id)
            if not assignment:
                raise ValueError("Fee assignment not found")

            receipt = self._payment_repo.get_next_receipt_number(session, assignment.institution_id)
            result = self._payment_repo.create(session, ctx, assignment.institution_id, dto, receipt)

            # Auto-update assignment status (D11)
            total = self._fee_assignment_repo.get_total_payments(session, dto.fee_assignment_id)
            if total >= assignment.amount:
                self._fee_assignment_repo.update(session, ctx, dto.fee_assignment_id,
                                                 FeeAssignmentUpdateDTO(status="paid"))
            elif total > 0:
                self._fee_assignment_repo.update(session, ctx, dto.fee_assignment_id,
                                                 FeeAssignmentUpdateDTO(status="partial"))

            session.commit()

            if self._audit:
                self._audit.emit(action="payment_recorded", client_id=ctx.client_id, institution_id=ctx.institution_id,
                                 actor=ctx.user_id or "system",
                                 payload={"payment_id": str(result.id),
                                  "assignment_id": str(dto.fee_assignment_id),
                                  "amount": str(dto.amount), "method": dto.payment_method,
                                  "receipt_number": receipt})
            return result

    def list_payments(self, ctx: TenantContext, fee_assignment_id: uuid.UUID | None = None,
                      user_id: uuid.UUID | None = None) -> list[PaymentDTO]:
        self._enforce_ownership(ctx, user_id)
        with self._session_factory() as session:
            return self._payment_repo.list_with_filters(session, ctx, fee_assignment_id, user_id)

    # ---- Ownership (D13) ----

    STUDENT_PARENT_ROLES = {"Student", "Parent"}

    def _enforce_ownership(self, ctx: TenantContext, requested_user_id: uuid.UUID | None) -> None:
        if requested_user_id and ctx.roles:
            if any(r in self.STUDENT_PARENT_ROLES for r in ctx.roles):
                if str(requested_user_id) != str(ctx.user_id):
                    raise ValueError("You can only access your own records")
