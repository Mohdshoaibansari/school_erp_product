"""Approval + ownership-transfer repository (Q3, D12, AC-11, AC-19)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.models import (
    Approval,
    Institution,
    OrgUnit,
    OwnershipTransferEvent,
)
from kernel.tenant_institution.repos.base import TenantAwareRepositoryBase
from kernel.tenant_institution.services.dtos import (
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

    def __init__(self) -> None:
        self._approval_repo = ApprovalRepository()

    def request_transfer(
        self, session: Session, ctx: TenantContext,
        institution_id: uuid.UUID, to_client_id: uuid.UUID,
        reason: str | None,
    ) -> ApprovalDTO:
        """Request an ownership transfer (D12 step 1).

        Creates a pending Approval row (Q3, AC-19). The transfer cannot
        complete until the Approval is granted (sub-phase C task 8.4).
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
    ) -> OwnershipTransferEventDTO:
        """Approve and execute the ownership transfer (D12, AC-11).

        Executes in a single transaction: updates ``institution.client_id``
        and all ``org_unit.client_id`` from A→B. Records an
        ``OwnershipTransferEvent``.

        NOTE: C-05 academic structure + C-02 student/user record updates are
        downstream coordination points (owned by C-05/C-02). C-11 audit
        emission is deferred to Apply-D (task 13.4). The transaction boundary
        is in place; downstream tables will be added when those capabilities
        exist.
        """
        # Mark Approval as approved (Q3, AC-19)
        approval = self._approval_repo.approve(
            session, ctx, approval_id, ctx.user_id or "platform_owner",
        )

        # Single-transaction transfer (D12, AC-11)
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

        # Record OwnershipTransferEvent (D12)
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

        # C-11 audit emission deferred to Apply-D (task 13.4).
        # Post-move isolation verification deferred to Apply-C (task 11.3).

        return OwnershipTransferEventDTO.model_validate(event)
