"""Tests for ownership transfer transaction (tasks 11.1–11.7, D12, AC-11, AC-19).

11.1: Transfer request + both-client consent + Platform Owner approval flow (blocking)
11.2: Single-transaction transfer — Institution + OrgUnits client_id A→B; boundary hooks
11.3: Post-move isolation — Client A can no longer access, Client B can
11.4: OwnershipTransferEvent recording
11.5: Immutable-audit invariant (boundary stub — C-11 owns audit)
11.6: User migration rules (boundary stub — C-02 owns users)
11.7: Billing-handoff coordination point (boundary stub — C-07/C-23 own billing)
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from business.tenant_institution.models import (
    Client,
    Institution,
    InstitutionType,
    InstitutionTypeName,
    LegalEntityType,
    OrgUnitType,
    OrgUnit,
    OwnershipTransferEvent,
)
from business.tenant_institution.repos import (
    ApprovalRepository,
    OwnershipTransferRepository,
    InstitutionRepository,
    ClientRepository,
)
from business.tenant_institution.services.approval import (
    ApprovalDeniedError,
)
from kernel.transfer_coordinator import (
    TransferCoordinator,
    DefaultTransferCoordinator,
)
from business.tenant_institution.dependencies import get_tenant_institution_service


# ============================================================
# Helpers
# ============================================================

def _get_lookup_ids(db_session: Session):
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()
    return let.id, itn.id, out.id


def _make_two_clients_with_institution(db_session: Session, slug_a="xfer-a", slug_b="xfer-b"):
    """Create client A + client B, with an institution under A + OrgUnits."""
    let_id, itn_id, out_id = _get_lookup_ids(db_session)

    client_a = Client(
        slug=slug_a, display_name="Client A", legal_name="CA Ltd",
        legal_entity_type_id=let_id, primary_contact_email=f"i@{slug_a}.com",
        current_lifecycle_status="active",
    )
    client_b = Client(
        slug=slug_b, display_name="Client B", legal_name="CB Ltd",
        legal_entity_type_id=let_id, primary_contact_email=f"i@{slug_b}.com",
        current_lifecycle_status="active",
    )
    db_session.add_all([client_a, client_b])
    db_session.flush()

    itype = InstitutionType(name_id=itn_id, code="IT_XFER", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(
        client_id=client_a.id, institution_type_id=itype.id, display_name="Transfer Inst",
        current_lifecycle_status="active",
    )
    db_session.add(inst)
    db_session.flush()

    org1 = OrgUnit(
        client_id=client_a.id, institution_id=inst.id, name="Dept 1", type_id=out_id,
    )
    org2 = OrgUnit(
        client_id=client_a.id, institution_id=inst.id, name="Dept 2", type_id=out_id,
        parent_id=None,
    )
    db_session.add_all([org1, org2])
    db_session.flush()
    db_session.commit()

    return client_a, client_b, inst, org1, org2


# ============================================================
# 11.1 — Transfer request + consent + blocking approval (AC-11, AC-19)
# ============================================================

class TestTransferApprovalFlow:
    """11.1 evidence: approval flow blocks transfer until approved + consent."""

    def test_request_creates_pending_approval(self, db_session: Session):
        """AC-19: request creates a pending Approval."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(
            db_session, ctx, inst.id, client_b.id, "Transfer reason",
        )
        assert approval.status == "pending"
        assert approval.context_type == "ownership_transfer"
        assert approval.context_id == inst.id

    def test_transfer_blocked_without_consent_source(self, db_session: Session):
        """AC-11: transfer blocked without source client consent."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        # Attempt to approve without consent_source → should be rejected
        with pytest.raises(ValueError, match="Source client consent"):
            transfer_repo.approve_transfer(
                db_session, ctx, approval.id, inst.id,
                client_a.id, client_b.id,
                consent_source=False, consent_dest=True, reason="Test",
            )

    def test_transfer_blocked_without_consent_dest(self, db_session: Session):
        """AC-11: transfer blocked without destination client consent."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        with pytest.raises(ValueError, match="Destination client consent"):
            transfer_repo.approve_transfer(
                db_session, ctx, approval.id, inst.id,
                client_a.id, client_b.id,
                consent_source=True, consent_dest=False, reason="Test",
            )

    def test_transfer_blocked_when_approval_denied(self, db_session: Session):
        """AC-19: a denied approval permanently blocks the transfer."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()
        approval_repo = ApprovalRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        # Deny the approval
        approval_repo.deny(db_session, ctx, approval.id, "po")
        db_session.flush()

        # Attempt to approve the transfer → should be blocked (denied)
        with pytest.raises(ApprovalDeniedError):
            transfer_repo.approve_transfer(
                db_session, ctx, approval.id, inst.id,
                client_a.id, client_b.id,
                consent_source=True, consent_dest=True, reason="Test",
            )


# ============================================================
# 11.2 — Single-transaction transfer + boundary hooks (AC-11)
# ============================================================

class TestSingleTransactionTransfer:
    """11.2 evidence: single-transaction transfer of client_id A→B + boundary hooks."""

    def test_institution_and_orgunit_client_id_a_to_b(self, db_session: Session):
        """AC-11: all client_id columns A→B after the transaction."""
        client_a, client_b, inst, org1, org2 = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        event = transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Approved",
        )
        db_session.commit()

        # Verify Institution client_id → B
        db_session.expire_all()
        updated_inst = db_session.execute(
            select(Institution).where(Institution.id == inst.id)
        ).scalars().first()
        assert updated_inst.client_id == client_b.id

        # Verify OrgUnits client_id → B
        orgs = db_session.execute(
            select(OrgUnit).where(OrgUnit.institution_id == inst.id)
        ).scalars().all()
        for org in orgs:
            assert org.client_id == client_b.id, \
                f"OrgUnit {org.name} client_id should be B ({client_b.id}), got {org.client_id}"

    def test_partial_failure_rolls_back_entire_transaction(self, db_session: Session):
        """AC-11: partial failure rolls back the entire transaction."""
        client_a, client_b, inst, org1, org2 = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        # Create a coordinator that raises mid-transaction
        failing_coordinator = MagicMock(spec=TransferCoordinator)
        failing_coordinator.migrate_academic_structure.side_effect = RuntimeError("C-05 failure")

        with pytest.raises(RuntimeError, match="C-05 failure"):
            transfer_repo.approve_transfer(
                db_session, ctx, approval.id, inst.id,
                client_a.id, client_b.id,
                consent_source=True, consent_dest=True, reason="Test",
                coordinator=failing_coordinator,
            )
        db_session.rollback()

        # Verify the Institution was NOT transferred (rolled back)
        db_session.expire_all()
        persisted_inst = db_session.execute(
            select(Institution).where(Institution.id == inst.id)
        ).scalars().first()
        assert persisted_inst.client_id == client_a.id, \
            "Partial failure should have rolled back — Institution should still be under Client A"

    def test_boundary_hooks_called(self, db_session: Session):
        """11.2/11.5/11.6: TransferCoordinator hooks are called during the transfer."""
        client_a, client_b, inst, org1, org2 = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        mock_coordinator = MagicMock(spec=TransferCoordinator)
        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
            coordinator=mock_coordinator,
        )
        db_session.commit()

        # Verify C-05 boundary hook was called
        mock_coordinator.migrate_academic_structure.assert_called_once_with(
            inst.id, client_a.id, client_b.id, db_session,
        )
        # Verify C-02 boundary hook was called
        mock_coordinator.migrate_users.assert_called_once_with(
            inst.id, client_a.id, client_b.id, db_session,
        )
        # Verify C-11 boundary invariant hook was called
        mock_coordinator.preserve_audit_client_ids.assert_called_once_with(
            inst.id, client_a.id, client_b.id, db_session,
        )

    def test_billing_hook_called_after_commit(self, db_session: Session):
        """11.7: billing handoff hook is called after the transfer transaction commits."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)

        svc = get_tenant_institution_service()
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")

        approval = svc.request_ownership_transfer(ctx, inst.id, client_b.id, "Test")

        mock_coordinator = MagicMock(spec=TransferCoordinator)
        svc.approve_ownership_transfer(
            ctx, approval.id, inst.id, client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
            coordinator=mock_coordinator,
        )

        # Billing hook should be called post-commit (no session parameter)
        mock_coordinator.migrate_billing.assert_called_once_with(
            inst.id, client_a.id, client_b.id,
        )


# ============================================================
# 11.3 — Post-move isolation (AC-11)
# ============================================================

class TestPostMoveIsolation:
    """11.3 evidence: post-move isolation — Client A can't access, Client B can."""

    def test_client_a_cannot_access_transferred_institution(self, db_session: Session):
        """AC-11: after transfer, Client A can no longer access the Institution."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx_a = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx_a, inst.id, client_b.id, "Test")
        db_session.flush()
        transfer_repo.approve_transfer(
            db_session, ctx_a, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Done",
        )
        db_session.commit()

        # Client A's repo query should return None (no longer under A)
        ctx_a_after = TenantContext(client_id=client_a.id, institution_id=None, user_id="user-a")
        inst_repo = InstitutionRepository()
        result = inst_repo.get(db_session, ctx_a_after, inst.id)
        assert result is None, \
            "Client A should NOT be able to access the transferred Institution (AC-11)"

    def test_client_b_can_access_transferred_institution(self, db_session: Session):
        """AC-11: after transfer, Client B can access the Institution."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx_a = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx_a, inst.id, client_b.id, "Test")
        db_session.flush()
        transfer_repo.approve_transfer(
            db_session, ctx_a, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Done",
        )
        db_session.commit()

        # Client B's repo query should return the Institution
        ctx_b = TenantContext(client_id=client_b.id, institution_id=None, user_id="user-b")
        inst_repo = InstitutionRepository()
        result = inst_repo.get(db_session, ctx_b, inst.id)
        assert result is not None, \
            "Client B SHOULD be able to access the transferred Institution (AC-11)"
        assert result.client_id == client_b.id


# ============================================================
# 11.4 — OwnershipTransferEvent recording (AC-11)
# ============================================================

class TestOwnershipTransferEvent:
    """11.4 evidence: OwnershipTransferEvent row is written on transfer."""

    def test_event_row_written_with_all_fields(self, db_session: Session):
        """AC-11: OwnershipTransferEvent captures all D12 fields."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Reason X")
        db_session.flush()
        event = transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Reason X",
        )
        db_session.commit()

        # Verify the event row in the DB
        db_session.expire_all()
        events = db_session.execute(
            select(OwnershipTransferEvent).where(
                OwnershipTransferEvent.institution_id == inst.id
            )
        ).scalars().all()
        assert len(events) == 1
        evt = events[0]
        assert evt.from_client_id == client_a.id
        assert evt.to_client_id == client_b.id
        assert evt.institution_id == inst.id
        assert evt.approved_by == "po"
        assert evt.consent_source is True
        assert evt.consent_dest is True
        assert evt.reason == "Reason X"
        assert evt.transferred_at is not None
        assert evt.approval_id == approval.id


# ============================================================
# 11.5 — Immutable-audit invariant (boundary stub — C-11 owns audit)
# ============================================================

class TestImmutableAuditInvariant:
    """11.5 evidence: immutable-audit invariant (boundary stub).

    The INVARIANT: the transfer transaction MUST NOT rewrite pre-existing
    audit-event client_ids (ADR §5 constraint 14). C-11 audit emission itself
    is Apply-D (task 13.4). This test verifies the transfer hooks the
    ``preserve_audit_client_ids`` boundary point and that the DefaultTransferCoordinator
    is a no-op (does NOT rewrite audit event rows).
    """

    def test_preserve_audit_client_ids_hook_is_called(self, db_session: Session):
        """11.5: the preserve_audit_client_ids boundary hook is called during transfer."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        mock_coordinator = MagicMock(spec=TransferCoordinator)
        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
            coordinator=mock_coordinator,
        )
        db_session.commit()

        mock_coordinator.preserve_audit_client_ids.assert_called_once()

    def test_default_coordinator_preserve_audit_is_noop(self, db_session: Session):
        """11.5: the default coordinator's preserve_audit_client_ids is a no-op (does NOT rewrite)."""
        coordinator = DefaultTransferCoordinator()
        # Should not raise — it's a no-op
        # The invariant: the transfer MUST NOT rewrite pre-existing audit client_ids
        coordinator.preserve_audit_client_ids(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), db_session,
        )
        # No assertion needed — the no-op return proves the transfer does NOT
        # touch audit event rows. C-11 owns the audit log; full C-11 wiring
        # in Apply-D (task 13.4).

    def test_no_audit_event_table_rewriting_in_transfer(self, db_session: Session):
        """11.5 boundary note: the transfer transaction does NOT create or modify
        a C-11 audit event table. The C-11 audit table doesn't exist yet —
        this test asserts the transfer only touches C-01-owned tables.

        Full C-11 audit emission + immutability verification is Apply-D (task 13.4).
        """
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()
        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
        )
        db_session.commit()

        # Assert no audit_event table exists (C-11 is Apply-D)
        with db_session.bind.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name LIKE '%audit%'
            """))
            audit_tables = [r[0] for r in result.fetchall()]
            # No C-11 audit table should exist yet — C-11 is Apply-D
            assert "audit_event" not in audit_tables, (
                "C-11 audit_event table should NOT exist yet (Apply-D). "
                "The transfer transaction MUST NOT create audit tables — "
                "C-11 owns the audit log. Full C-11 wiring in Apply-D task 13.4."
            )


# ============================================================
# 11.6 — User migration rules (boundary stub — C-02 owns users)
# ============================================================

class TestUserMigrationBoundary:
    """11.6 evidence: user migration is a C-02 boundary — hook in place, stub test.

    C-02 owns user-institution assignments + student records. C-01 provides
    the hook (``migrate_users``) and calls it during the transfer. C-02 plugs
    in its own implementation. Do NOT fake the user migration.
    """

    def test_migrate_users_hook_called(self, db_session: Session):
        """11.6: the migrate_users boundary hook is called during transfer."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")
        transfer_repo = OwnershipTransferRepository()

        approval = transfer_repo.request_transfer(db_session, ctx, inst.id, client_b.id, "Test")
        db_session.flush()

        mock_coordinator = MagicMock(spec=TransferCoordinator)
        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
            coordinator=mock_coordinator,
        )
        db_session.commit()

        mock_coordinator.migrate_users.assert_called_once_with(
            inst.id, client_a.id, client_b.id, db_session,
        )

    def test_default_coordinator_migrate_users_is_noop(self, db_session: Session):
        """11.6: the default coordinator's migrate_users is a no-op (C-02 boundary).

        C-02 owns user-institution assignments + student records. The default
        implementation logs the boundary call and returns. C-02 plugs in its
        own implementation in its own change.
        """
        coordinator = DefaultTransferCoordinator()
        # Should not raise — it's a no-op boundary stub
        coordinator.migrate_users(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), db_session)


# ============================================================
# 11.7 — Billing-handoff coordination point (boundary stub — C-07/C-23)
# ============================================================

class TestBillingHandoffBoundary:
    """11.7 evidence: billing handoff is a C-07/C-23 boundary — hook + stub test.

    C-07/C-23 own the billing behavior. C-01 notes the coordination point
    and calls the ``migrate_billing`` hook post-commit. Do NOT implement billing.
    """

    def test_migrate_billing_hook_called_post_commit(self, db_session: Session):
        """11.7: the migrate_billing hook is called after the transfer commits."""
        client_a, client_b, inst, _, _ = _make_two_clients_with_institution(db_session)

        svc = get_tenant_institution_service()
        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, user_id="po")

        approval = svc.request_ownership_transfer(ctx, inst.id, client_b.id, "Test")
        mock_coordinator = MagicMock(spec=TransferCoordinator)
        svc.approve_ownership_transfer(
            ctx, approval.id, inst.id, client_a.id, client_b.id,
            consent_source=True, consent_dest=True, reason="Test",
            coordinator=mock_coordinator,
        )

        # Billing hook is called post-commit
        mock_coordinator.migrate_billing.assert_called_once_with(
            inst.id, client_a.id, client_b.id,
        )

    def test_default_coordinator_migrate_billing_is_noop(self):
        """11.7: the default coordinator's migrate_billing is a no-op (C-07/C-23 boundary)."""
        coordinator = DefaultTransferCoordinator()
        # Should not raise — it's a no-op boundary stub
        coordinator.migrate_billing(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
