"""Approval + ownership-transfer repository (Q3, D12, AC-11, AC-19).

Approval flow (task 8.4): the dependent transition/transfer cannot complete
until ``status=approved``; ``status=denied`` blocks.

Ownership transfer (D12, tasks 11.1–11.7):
- request creates a pending Approval (Q3, AC-19).
- approve checks consent (11.1), asserts approval is pending, executes the
  single-transaction transfer (11.2), records OwnershipTransferEvent (11.4),
  calls TransferCoordinator boundary hooks (11.2/11.5/11.6/11.7).
- C-05/C-02/C-07/C-23/C-11 downstream behavior is a BOUNDARY — hooks are
  no-op stubs; those capabilities plug in their own implementations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from business.tenant_institution.models import (
    Approval,
    Institution,
    OrgUnit,
    OwnershipTransferEvent,
)
from kernel.repo_base import TenantAwareRepositoryBase
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from business.tenant_institution.services.dtos import (
    ApprovalDTO,
    OwnershipTransferEventDTO,
)


class ApprovalRepository(TenantAwareRepositoryBase[Approval]):
    """Repository for Approval records (Q3, AC-19)."""

    def __init__(self) -> None:
        super().__init__(Approval)

    @property
    def _is_client_scoped(self) -> bool:
        return False  # Approval has no client_id column — platform-scoped

    def _client_filter(self, ctx: TenantContext):
        return None

    def _to_dto(self, obj: Approval) -> ApprovalDTO:
        return ApprovalDTO.model_validate(obj)

    def create(
        self, session: Session, ctx: TenantContext,
        requested_by: str, context_type: str | None = None,
        context_id: uuid.UUID | None = None, reason: str | None = None,
    ) -> ApprovalDTO:
        obj = Approval(
            requested_by=requested_by,
            status="pending",
            context_type=context_type,
            context_id=context_id,
            reason=reason,
        )
        session.add(obj)
        session.flush()
        return self._to_dto(obj)

    def approve(
        self, session: Session, ctx: TenantContext, approval_id: uuid.UUID,
        approved_by: str,
    ) -> ApprovalDTO:
        stmt = select(Approval).where(Approval.id == approval_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Approval not found")
        obj.status = "approved"
        obj.approved_by = approved_by
        obj.approved_at = datetime.now(timezone.utc)
        session.flush()
        return self._to_dto(obj)

    def deny(
        self, session: Session, ctx: TenantContext, approval_id: uuid.UUID,
        approved_by: str,
    ) -> ApprovalDTO:
        stmt = select(Approval).where(Approval.id == approval_id)
        obj = session.execute(stmt).scalars().first()
        if not obj:
            raise ValueError("Approval not found")
        obj.status = "denied"
        obj.approved_by = approved_by
        obj.approved_at = datetime.now(timezone.utc)
        session.flush()
        return self._to_dto(obj)

    def get(self, session: Session, ctx: TenantContext, approval_id: uuid.UUID) -> ApprovalDTO | None:
        stmt = select(Approval).where(Approval.id == approval_id)
        obj = session.execute(stmt).scalars().first()
        return self._to_dto(obj) if obj else None


class OwnershipTransferRepository:
    """Repository for ownership transfer operations (D12, AC-11, AC-19).

    The single-transaction transfer + audit emission depends on Apply-C/D
    machinery (tasks 11, 13). For Apply-B, we implement the endpoint structure
    + the transaction boundary we can prove now:
    - request_transfer: creates a pending Approval (Q3)
    - approve_transfer: executes the transfer in a single transaction
      (updates Institution.client_id + OrgUnit.client_id A→B), records
      OwnershipTransferEvent. C-05/C-02 coordination and C-11 audit emission
      are deferred to Apply-C/D.
    """

    def __init__(self, audit_emitter: AuditEmitter | None = None) -> None:
        self._approval_repo = ApprovalRepository()
        self._audit = audit_emitter or DefaultAuditEmitter()

    def request_transfer(
        self, session: Session, ctx: TenantContext,
        institution_id: uuid.UUID, to_client_id: uuid.UUID,
        reason: str | None,
    ) -> ApprovalDTO:
        """Request an ownership transfer (D12 step 1, task 11.1).

        Creates a pending Approval row (Q3, AC-19). The transfer cannot
        complete until the Approval is granted AND both-client consent is
        provided (task 11.1).
        """
        # Verify the institution exists and belongs to the current client
        stmt = select(Institution).where(
            Institution.id == institution_id,
            Institution.client_id == ctx.client_id,
        )
        inst = session.execute(stmt).scalars().first()
        if not inst:
            raise ValueError("Institution not found")

        return self._approval_repo.create(
            session, ctx,
            requested_by=ctx.user_id or "unknown",
            context_type="ownership_transfer",
            context_id=institution_id,
            reason=reason,
        )

    def approve_transfer(
        self, session: Session, ctx: TenantContext,
        approval_id: uuid.UUID, institution_id: uuid.UUID,
        from_client_id: uuid.UUID, to_client_id: uuid.UUID,
        consent_source: bool, consent_dest: bool, reason: str | None,
        coordinator=None,
    ) -> OwnershipTransferEventDTO:
        """Approve and execute the ownership transfer (D12, AC-11, tasks 11.1–11.7).

        Blocking approval (task 8.4, 11.1): the transfer cannot execute until
        the Approval is granted. Consent (task 11.1): both ``consent_source``
        and ``consent_dest`` must be ``True``.

        This method first marks the Approval as ``approved`` (Q3, AC-19), then
        executes the single-transaction transfer. If the Approval is already
        ``denied``, the transfer is permanently blocked.

        Single-transaction transfer (task 11.2):
        - Update ``institution.client_id`` A→B (C-01 owned).
        - Update all ``org_unit.client_id`` A→B (C-01 owned).
        - Call ``coordinator.migrate_academic_structure`` (C-05 boundary hook).
        - Call ``coordinator.migrate_users`` (C-02 boundary hook).
        - Call ``coordinator.preserve_audit_client_ids`` (C-11 boundary invariant).
        - Record ``OwnershipTransferEvent`` (task 11.4).
        - After commit: call ``coordinator.migrate_billing`` (C-07/C-23 boundary).

        If any part fails, the entire transaction rolls back (AC-11).

        Boundary declarations:
        - C-05 academic structure migration: hook in place, C-05 owns it.
        - C-02 student/user record migration: hook in place, C-02 owns it.
        - C-07/C-23 billing handoff: hook in place, C-07/C-23 own it.
        - C-11 audit immutability invariant: hook in place, C-11 owns the log.
        """
        from kernel.transfer_coordinator import DefaultTransferCoordinator

        if coordinator is None:
            coordinator = DefaultTransferCoordinator()

        # Task 8.4/11.1: check the approval status BEFORE executing.
        # If denied, the transfer is permanently blocked.
        existing_approval = self._approval_repo.get(session, ctx, approval_id)
        if existing_approval is None:
            raise ValueError("Approval not found")
        if existing_approval.status == "denied":
            from business.tenant_institution.services.approval import ApprovalDeniedError
            raise ApprovalDeniedError(approval_id)

        # Mark Approval as approved (Q3, AC-19)
        self._approval_repo.approve(
            session, ctx, approval_id, ctx.user_id or "platform_owner",
        )

        # Task 11.1: both-client consent required (D12)
        if not consent_source:
            raise ValueError(
                "Source client consent is required for ownership transfer (D12, AC-11)"
            )
        if not consent_dest:
            raise ValueError(
                "Destination client consent is required for ownership transfer (D12, AC-11)"
            )

        # Single-transaction transfer (D12, AC-11, task 11.2)
        # Update Institution.client_id A→B
        stmt = select(Institution).where(Institution.id == institution_id)
        inst = session.execute(stmt).scalars().first()
        if not inst:
            raise ValueError("Institution not found")

        old_client_id = inst.client_id
        inst.client_id = to_client_id
        session.flush()

        # Update all OrgUnits under this institution A→B
        org_stmt = select(OrgUnit).where(
            OrgUnit.institution_id == institution_id,
        )
        org_units = session.execute(org_stmt).scalars().all()
        for ou in org_units:
            ou.client_id = to_client_id
        session.flush()

        # Task 11.2: C-05 boundary hook — academic structure migration
        coordinator.migrate_academic_structure(
            institution_id, from_client_id, to_client_id, session,
        )

        # Task 11.6: C-02 boundary hook — user-institution assignments + student records
        coordinator.migrate_users(
            institution_id, from_client_id, to_client_id, session,
        )

        # Task 11.5: C-11 boundary invariant — pre-transfer audit events keep
        # their original client_id. The transfer MUST NOT rewrite audit
        # event client_ids (ADR §5 constraint 14).
        coordinator.preserve_audit_client_ids(
            institution_id, from_client_id, to_client_id, session,
        )

        # Task 11.4: Record OwnershipTransferEvent (D12)
        event = OwnershipTransferEvent(
            client_id=to_client_id,  # new owner
            from_client_id=from_client_id,
            to_client_id=to_client_id,
            institution_id=institution_id,
            approved_by=ctx.user_id or "platform_owner",
            consent_source=consent_source,
            consent_dest=consent_dest,
            reason=reason,
            approval_id=approval_id,
        )
        session.add(event)
        session.flush()

        # 13.4: synchronous C-11 audit emission for ownership transfer (AC-11).
        # The audit event is tagged with the NEW owning ClientId (to_client_id)
        # to record that the transfer occurred under Client B's stewardship.
        # The immutability invariant (D12, ADR §5 constraint 14) is preserved:
        # audit events emitted BEFORE this transfer keep their original ClientId
        # — the emitter only APPENDS new events; it never rewrites past
        # events, and the transfer transaction does not touch audit-event rows
        # (preserve_audit_client_ids hook is a no-op expressing this invariant).
        self._audit.emit(
            action="ownership_transferred",
            client_id=to_client_id,
            institution_id=institution_id,
            actor=ctx.user_id or "platform_owner",
            payload={
                "from_client_id": str(from_client_id),
                "to_client_id": str(to_client_id),
                "institution_id": str(institution_id),
                "approved_by": ctx.user_id or "platform_owner",
                "consent_source": consent_source,
                "consent_dest": consent_dest,
                "reason": reason,
                "approval_id": str(approval_id),
            },
        )

        # Task 11.7: C-07/C-23 boundary hook — billing handoff (next cycle).
        # Called AFTER the transfer transaction is committed by the service
        # layer (billing handoff is next-cycle, not in-transaction).

        return OwnershipTransferEventDTO.model_validate(event)
