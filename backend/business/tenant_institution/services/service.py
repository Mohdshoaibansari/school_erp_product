"""C-01 services — published interface (A4).

Services orchestrate repos + ``TenantContext``. Endpoints call services;
services call repos. This is the module boundary other modules see.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from kernel.tenant_context import TenantContext
from business.tenant_institution.repos import (
    ApprovalRepository,
    ClientRepository,
    InstitutionRepository,
    InstitutionTypeRepository,
    OrgUnitRepository,
    OwnershipTransferRepository,
)
from kernel.audit import AuditEmitter, DefaultAuditEmitter
from business.tenant_institution.services.dtos import (
    ApprovalDTO,
    ClientCreateDTO,
    ClientDTO,
    ClientUpdateDTO,
    InstitutionCreateDTO,
    InstitutionDTO,
    InstitutionTypeCreateDTO,
    InstitutionTypeDTO,
    InstitutionTypeUpdateDTO,
    InstitutionUpdateDTO,
    OrgUnitCreateDTO,
    OrgUnitDTO,
    OwnershipTransferEventDTO,
)


class TenantInstitutionService:
    """Published service interface for C-01 (A4).

    Endpoints call this; it orchestrates repos + TenantContext.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_emitter: AuditEmitter | None = None,
        client_repo: ClientRepository | None = None,
        institution_repo: InstitutionRepository | None = None,
        institution_type_repo: InstitutionTypeRepository | None = None,
        org_unit_repo: OrgUnitRepository | None = None,
        approval_repo: ApprovalRepository | None = None,
        transfer_repo: OwnershipTransferRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        # 13.x: shared synchronous C-11 audit emitter (boundary hook). Tests
        # inject a capture emitter; production uses the default capture stub
        # until C-11 plugs in real persistence.
        self._audit = audit_emitter or DefaultAuditEmitter()
        self._client_repo = client_repo or ClientRepository(audit_emitter=self._audit)
        self._institution_repo = institution_repo or InstitutionRepository(audit_emitter=self._audit)
        self._institution_type_repo = institution_type_repo or InstitutionTypeRepository()
        self._org_unit_repo = org_unit_repo or OrgUnitRepository(audit_emitter=self._audit)
        self._approval_repo = approval_repo or ApprovalRepository()
        self._transfer_repo = transfer_repo or OwnershipTransferRepository(audit_emitter=self._audit)

    @property
    def audit_emitter(self) -> AuditEmitter:
        """Expose the shared audit emitter for tests (13.x)."""
        return self._audit

    # ---- Client ----

    def create_client(self, ctx: TenantContext, dto: ClientCreateDTO) -> ClientDTO:
        with self._session_factory() as session:
            return self._client_repo.create(session, ctx, dto)

    def get_client(self, ctx: TenantContext, client_id: uuid.UUID) -> ClientDTO | None:
        with self._session_factory() as session:
            return self._client_repo.get_by_id(session, ctx, client_id)

    def list_clients(self, ctx: TenantContext) -> list[ClientDTO]:
        with self._session_factory() as session:
            return self._client_repo.list_all(session, ctx)

    def update_client(
        self, ctx: TenantContext, client_id: uuid.UUID, dto: ClientUpdateDTO,
    ) -> ClientDTO:
        with self._session_factory() as session:
            return self._client_repo.update_identity(session, ctx, client_id, dto)

    def transition_client_lifecycle(
        self, ctx: TenantContext, client_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> ClientDTO:
        with self._session_factory() as session:
            return self._client_repo.transition_lifecycle(
                session, ctx, client_id, new_state, reason, ctx.user_id or "unknown",
            )

    # ---- Institution ----

    def create_institution(
        self, ctx: TenantContext, dto: InstitutionCreateDTO,
    ) -> InstitutionDTO:
        with self._session_factory() as session:
            result = self._institution_repo.create(session, ctx, dto)
            session.commit()
            return result

    def list_institutions(
        self, ctx: TenantContext, *, cross_institution: bool = False,
    ) -> list[InstitutionDTO]:
        with self._session_factory() as session:
            return self._institution_repo.list(
                session, ctx, cross_institution=cross_institution,
            )

    def get_institution(
        self, ctx: TenantContext, institution_id: uuid.UUID,
    ) -> InstitutionDTO | None:
        with self._session_factory() as session:
            return self._institution_repo.get(session, ctx, institution_id)

    def update_institution(
        self, ctx: TenantContext, institution_id: uuid.UUID,
        dto: InstitutionUpdateDTO,
    ) -> InstitutionDTO:
        with self._session_factory() as session:
            result = self._institution_repo.update_identity(session, ctx, institution_id, dto)
            session.commit()
            return result

    def transition_institution_lifecycle(
        self, ctx: TenantContext, institution_id: uuid.UUID,
        new_state: str, reason: str | None,
    ) -> InstitutionDTO:
        with self._session_factory() as session:
            result = self._institution_repo.transition_lifecycle(
                session, ctx, institution_id, new_state, reason, ctx.user_id or "unknown",
            )
            session.commit()
            return result

    # ---- InstitutionType ----

    def create_institution_type(
        self, ctx: TenantContext, dto: InstitutionTypeCreateDTO,
    ) -> InstitutionTypeDTO:
        with self._session_factory() as session:
            result = self._institution_type_repo.create(session, ctx, dto)
            session.commit()
            return result

    def update_institution_type_template(
        self, ctx: TenantContext, itype_id: uuid.UUID,
        dto: InstitutionTypeUpdateDTO,
    ) -> InstitutionTypeDTO:
        with self._session_factory() as session:
            result = self._institution_type_repo.update_template(session, ctx, itype_id, dto)
            session.commit()
            return result

    def list_institution_types(self, ctx: TenantContext) -> list[InstitutionTypeDTO]:
        with self._session_factory() as session:
            return self._institution_type_repo.list_all(session, ctx)

    def get_institution_type(
        self, ctx: TenantContext, itype_id: uuid.UUID,
    ) -> InstitutionTypeDTO | None:
        with self._session_factory() as session:
            return self._institution_type_repo.get(session, ctx, itype_id)

    # ---- OrgUnit ----

    def create_org_unit(
        self, ctx: TenantContext, dto: OrgUnitCreateDTO,
    ) -> OrgUnitDTO:
        with self._session_factory() as session:
            result = self._org_unit_repo.create(session, ctx, dto)
            session.commit()
            return result

    def list_org_units(
        self, ctx: TenantContext, institution_id: uuid.UUID,
        *, cross_institution: bool = False,
    ) -> list[OrgUnitDTO]:
        with self._session_factory() as session:
            return self._org_unit_repo.list(
                session, ctx, cross_institution=cross_institution,
                institution_id=institution_id,
            )

    def move_org_unit(
        self, ctx: TenantContext, org_unit_id: uuid.UUID,
        new_parent_id: uuid.UUID | None,
    ) -> OrgUnitDTO:
        with self._session_factory() as session:
            result = self._org_unit_repo.move(session, ctx, org_unit_id, new_parent_id)
            session.commit()
            return result

    def archive_org_unit(
        self, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> OrgUnitDTO:
        with self._session_factory() as session:
            result = self._org_unit_repo.archive(session, ctx, org_unit_id)
            session.commit()
            return result

    def reactivate_org_unit(
        self, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> OrgUnitDTO:
        with self._session_factory() as session:
            result = self._org_unit_repo.reactivate(session, ctx, org_unit_id)
            session.commit()
            return result

    def reorder_org_unit(
        self, ctx: TenantContext, org_unit_id: uuid.UUID, sort_order: int,
    ) -> OrgUnitDTO:
        with self._session_factory() as session:
            result = self._org_unit_repo.reorder(session, ctx, org_unit_id, sort_order)
            session.commit()
            return result

    def get_org_unit_subtree(
        self, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> list[OrgUnitDTO]:
        with self._session_factory() as session:
            return self._org_unit_repo.get_subtree(session, ctx, org_unit_id)

    def get_org_unit_ancestors(
        self, ctx: TenantContext, org_unit_id: uuid.UUID,
    ) -> list[OrgUnitDTO]:
        """Get the full ancestor chain of an OrgUnit (task 9.3, D6)."""
        with self._session_factory() as session:
            return self._org_unit_repo.get_ancestors(session, ctx, org_unit_id)

    def update_org_unit_type(
        self, ctx: TenantContext, org_unit_id: uuid.UUID, new_type_id: uuid.UUID,
    ) -> OrgUnitDTO:
        """Reject OrgUnit type change — type is immutable (task 9.2, AC-8).

        Always raises ValueError. To change type, archive + recreate (D6).
        """
        with self._session_factory() as session:
            return self._org_unit_repo.update_type(session, ctx, org_unit_id, new_type_id)

    # ---- Effective-state gating (task 8.3, AC-7) ----

    def get_institution_effective_state(
        self, ctx: TenantContext, institution_id: uuid.UUID,
    ) -> str:
        """Compute the effective operational state at runtime (AC-7, task 8.3).

        Returns ``"active"`` if both Institution and Client are active,
        ``"gated"`` if the Institution is active but the Client is not
        (runtime gating without persisted mutation), or the Institution's
        own state otherwise.
        """
        with self._session_factory() as session:
            return self._institution_repo.get_effective_state(session, ctx, institution_id)

    # ---- Ownership transfer ----

    def request_ownership_transfer(
        self, ctx: TenantContext, institution_id: uuid.UUID,
        to_client_id: uuid.UUID, reason: str | None,
    ) -> ApprovalDTO:
        with self._session_factory() as session:
            result = self._transfer_repo.request_transfer(
                session, ctx, institution_id, to_client_id, reason,
            )
            session.commit()
            return result

    def approve_ownership_transfer(
        self, ctx: TenantContext, approval_id: uuid.UUID,
        institution_id: uuid.UUID, from_client_id: uuid.UUID,
        to_client_id: uuid.UUID, consent_source: bool,
        consent_dest: bool, reason: str | None,
        coordinator=None,
    ) -> OwnershipTransferEventDTO:
        """Approve and execute the ownership transfer (D12, AC-11, tasks 11.1–11.7).

        Executes in a single transaction (AC-11). Calls the TransferCoordinator
        boundary hooks for C-05/C-02/C-11 (in-transaction) and C-07/C-23
        (post-commit billing handoff).
        """
        from kernel.transfer_coordinator import DefaultTransferCoordinator

        if coordinator is None:
            coordinator = DefaultTransferCoordinator()

        with self._session_factory() as session:
            result = self._transfer_repo.approve_transfer(
                session, ctx, approval_id, institution_id,
                from_client_id, to_client_id,
                consent_source, consent_dest, reason,
                coordinator=coordinator,
            )
            session.commit()

        # Task 11.7: C-07/C-23 boundary — billing handoff (next cycle, post-commit)
        coordinator.migrate_billing(institution_id, from_client_id, to_client_id)

        return result
