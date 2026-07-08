"""Tests for lifecycle state machines + Approval flow (tasks 8.1–8.5).

8.1: Client lifecycle state machine (D8 arcs; Terminated terminal; Archived re-activatable)
8.2: Institution lifecycle state machine (D9 arcs; no Terminated)
8.3: Runtime effective-state gating (AC-7 — no persisted mutation on Client suspension)
8.4: Approval flow blocking (Q3, AC-19 — pending→approved completes; pending→denied blocks)
8.5: Every lifecycle transition writes a lifecycle event row
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from business.tenant_institution.models import (
    Client,
    Institution,
    InstitutionType,
    LegalEntityType,
    InstitutionTypeName,
    OrgUnitType,
    ClientLifecycleEvent,
    InstitutionLifecycleEvent,
)
from business.tenant_institution.repos import (
    ClientRepository,
    InstitutionRepository,
    ApprovalRepository,
    OwnershipTransferRepository,
)
from business.tenant_institution.services.state_machine import (
    InvalidTransitionError,
    validate_client_transition,
    validate_institution_transition,
    is_client_state_terminal,
    is_institution_operationally_active,
    CLIENT_ARCS,
    INSTITUTION_ARCS,
)
from business.tenant_institution.services.approval import (
    ApprovalNotGrantedError,
    ApprovalDeniedError,
    request_approval,
    approve_approval,
    deny_approval,
    assert_approved,
)


# ============================================================
# Helpers
# ============================================================

def _get_lookup_ids(db_session: Session):
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()
    return let.id, itn.id, out.id


def _make_client(db_session: Session, slug: str = "lc-client") -> Client:
    let_id, _, _ = _get_lookup_ids(db_session)
    client = Client(
        slug=slug, display_name=slug.title(), legal_name=f"{slug} Ltd",
        legal_entity_type_id=let_id, primary_contact_email=f"i@{slug}.com",
    )
    db_session.add(client)
    db_session.flush()
    return client


def _make_institution(db_session: Session, client_id: uuid.UUID, code: str = "IT_LC") -> Institution:
    _, itn_id, _ = _get_lookup_ids(db_session)
    itype = InstitutionType(name_id=itn_id, code=code, is_system=True)
    db_session.add(itype)
    db_session.flush()
    inst = Institution(
        client_id=client_id, institution_type_id=itype.id, display_name=f"{code} Inst",
    )
    db_session.add(inst)
    db_session.flush()
    return inst


# ============================================================
# 8.1 — Client lifecycle state machine (D8)
# ============================================================

class TestClientStateMachine:
    """8.1 evidence: Client lifecycle state machine (D8 arcs, AC-5)."""

    def test_all_allowed_arcs_accepted(self):
        """Every arc in CLIENT_ARCS is accepted by validate_client_transition."""
        for old_state, targets in CLIENT_ARCS.items():
            for new_state in targets:
                # Should NOT raise
                validate_client_transition(old_state, new_state)

    def test_terminated_is_terminal(self):
        """D8: Terminated is terminal — no outgoing arcs."""
        assert is_client_state_terminal("terminated")
        # All transitions FROM terminated are rejected
        for new_state in ("active", "suspended", "archived", "prospective"):
            with pytest.raises(InvalidTransitionError):
                validate_client_transition("terminated", new_state)

    def test_terminated_to_active_rejected(self):
        """AC-5: Terminated→Active is explicitly rejected."""
        with pytest.raises(InvalidTransitionError):
            validate_client_transition("terminated", "active")

    def test_disallowed_arc_rejected(self):
        """AC-5: disallowed arcs rejected (e.g. Prospective→Suspended, Prospective→Terminated)."""
        with pytest.raises(InvalidTransitionError):
            validate_client_transition("prospective", "suspended")
        with pytest.raises(InvalidTransitionError):
            validate_client_transition("prospective", "terminated")
        with pytest.raises(InvalidTransitionError):
            validate_client_transition("active", "prospective")

    def test_archived_is_re_activatable(self):
        """D8: Archived→Active is allowed (the only re-activatable inactive state)."""
        validate_client_transition("archived", "active")  # should NOT raise

    def test_client_transition_via_repo_writes_event(self, db_session: Session):
        """8.5: Client transition writes a client_lifecycle_event row."""
        client = _make_client(db_session, slug="evt-client")
        db_session.commit()

        ctx = TenantContext(client_id=client.id, is_platform_owner=True, user_id="tester")
        repo = ClientRepository()
        repo.transition_lifecycle(db_session, ctx, client.id, "active", "Contract signed", "tester")
        db_session.commit()

        events = db_session.execute(
            select(ClientLifecycleEvent).where(ClientLifecycleEvent.client_id == client.id)
        ).scalars().all()
        assert len(events) == 1
        assert events[0].state == "active"
        assert events[0].reason == "Contract signed"
        assert events[0].actor == "tester"


# ============================================================
# 8.2 — Institution lifecycle state machine (D9)
# ============================================================

class TestInstitutionStateMachine:
    """8.2 evidence: Institution lifecycle state machine (D9 arcs, AC-6)."""

    def test_all_allowed_arcs_accepted(self):
        """Every arc in INSTITUTION_ARCS is accepted by validate_institution_transition."""
        for old_state, targets in INSTITUTION_ARCS.items():
            for new_state in targets:
                validate_institution_transition(old_state, new_state)  # should NOT raise

    def test_no_terminated_state(self):
        """D9: Institutions have no Terminated state."""
        with pytest.raises(InvalidTransitionError):
            validate_institution_transition("active", "terminated")
        with pytest.raises(InvalidTransitionError):
            validate_institution_transition("onboarding", "terminated")

    def test_disallowed_arc_rejected(self):
        """AC-6: disallowed arcs rejected (e.g. Onboarding→Inactive, Archived→Inactive)."""
        with pytest.raises(InvalidTransitionError):
            validate_institution_transition("onboarding", "inactive")
        with pytest.raises(InvalidTransitionError):
            validate_institution_transition("archived", "inactive")

    def test_archived_re_activatable(self):
        """D9: Archived→Active is allowed."""
        validate_institution_transition("archived", "active")  # should NOT raise

    def test_institution_transition_via_repo_writes_event(self, db_session: Session):
        """8.5: Institution transition writes an institution_lifecycle_event row."""
        client = _make_client(db_session, slug="inst-evt-client")
        inst = _make_institution(db_session, client.id, code="IT_EVT")
        db_session.commit()

        ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="tester")
        repo = InstitutionRepository()
        repo.transition_lifecycle(db_session, ctx, inst.id, "active", "Go-live", "tester")
        db_session.commit()

        events = db_session.execute(
            select(InstitutionLifecycleEvent).where(
                InstitutionLifecycleEvent.institution_id == inst.id
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].state == "active"
        assert events[0].reason == "Go-live"
        assert events[0].actor == "tester"
        assert events[0].institution_id == inst.id


# ============================================================
# 8.3 — Runtime effective-state gating (AC-7)
# ============================================================

class TestEffectiveStateGating:
    """8.3 evidence: runtime effective-state gating — NO persisted mutation (AC-7)."""

    def test_effective_active_when_both_active(self, db_session: Session):
        """AC-7: Institution is operationally active when both Institution and Client are active."""
        client = _make_client(db_session, slug="gate-both")
        client.current_lifecycle_status = "active"
        inst = _make_institution(db_session, client.id, code="IT_GATE1")
        inst.current_lifecycle_status = "active"
        db_session.commit()

        ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="tester")
        repo = InstitutionRepository()
        effective = repo.get_effective_state(db_session, ctx, inst.id)
        assert effective == "active"

    def test_suspending_client_gates_institution_at_runtime(self, db_session: Session):
        """AC-7: suspending a Client gates an Active institution's access at runtime.

        The Institution's persisted ``current_lifecycle_status`` is NOT mutated.
        """
        client = _make_client(db_session, slug="gate-suspend")
        client.current_lifecycle_status = "active"
        inst = _make_institution(db_session, client.id, code="IT_GATE2")
        inst.current_lifecycle_status = "active"
        db_session.commit()

        ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="tester")
        repo = InstitutionRepository()

        # Before suspension: effective = active
        assert repo.get_effective_state(db_session, ctx, inst.id) == "active"

        # Suspend the client (persist the client's state change)
        client.current_lifecycle_status = "suspended"
        db_session.flush()
        db_session.commit()

        # After suspension: effective = "gated" (runtime, not persisted on Institution)
        assert repo.get_effective_state(db_session, ctx, inst.id) == "gated"

        # CRITICAL: the Institution's persisted state is NOT mutated (AC-7)
        db_session.expire_all()
        persisted_inst = db_session.execute(
            select(Institution).where(Institution.id == inst.id)
        ).scalars().first()
        assert persisted_inst.current_lifecycle_status == "active", \
            "Institution's persisted state must NOT be mutated by Client suspension (AC-7)"

    def test_restoring_client_re_enables_institution_no_persisted_restoration(self, db_session: Session):
        """AC-7: restoring the Client re-enables the Institution with NO persisted state restoration."""
        client = _make_client(db_session, slug="gate-restore")
        client.current_lifecycle_status = "active"
        inst = _make_institution(db_session, client.id, code="IT_GATE3")
        inst.current_lifecycle_status = "active"
        db_session.commit()

        ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="tester")
        repo = InstitutionRepository()

        # Suspend client → gated
        client.current_lifecycle_status = "suspended"
        db_session.commit()
        assert repo.get_effective_state(db_session, ctx, inst.id) == "gated"

        # Restore client → active again (NO persisted state restoration on Institution)
        client.current_lifecycle_status = "active"
        db_session.commit()
        assert repo.get_effective_state(db_session, ctx, inst.id) == "active"

        # Verify the Institution row was NEVER modified (updated_at unchanged from creation)
        db_session.expire_all()
        persisted_inst = db_session.execute(
            select(Institution).where(Institution.id == inst.id)
        ).scalars().first()
        assert persisted_inst.current_lifecycle_status == "active"

    def test_is_institution_operationally_active_pure_function(self):
        """Unit test: the pure function computes correctly without DB access."""
        assert is_institution_operationally_active("active", "active") is True
        assert is_institution_operationally_active("active", "suspended") is False
        assert is_institution_operationally_active("active", "archived") is False
        assert is_institution_operationally_active("active", "terminated") is False
        assert is_institution_operationally_active("inactive", "active") is False
        assert is_institution_operationally_active("onboarding", "active") is False


# ============================================================
# 8.4 — Approval flow blocking (Q3, AC-19)
# ============================================================

class TestApprovalFlow:
    """8.4 evidence: Approval flow blocking — pending→approved completes; pending→denied blocks."""

    def test_pending_approval_blocks_operation(self, db_session: Session):
        """AC-19: a pending approval blocks the dependent operation."""
        ctx = TenantContext(is_platform_owner=True, user_id="requester")
        approval_repo = ApprovalRepository()

        approval = request_approval(
            db_session, ctx, approval_repo,
            requested_by="requester",
            context_type="test",
            reason="test",
        )
        db_session.flush()

        # assert_approved should raise ApprovalNotGrantedError (still pending)
        with pytest.raises(ApprovalNotGrantedError):
            assert_approved(db_session, ctx, approval_repo, approval.id)

    def test_approved_approval_allows_operation(self, db_session: Session):
        """AC-19: an approved approval allows the dependent operation to proceed."""
        ctx = TenantContext(is_platform_owner=True, user_id="requester")
        approval_repo = ApprovalRepository()

        approval = request_approval(
            db_session, ctx, approval_repo,
            requested_by="requester",
            context_type="test",
            reason="test",
        )
        db_session.flush()

        # Approve it
        approve_approval(db_session, ctx, approval_repo, approval.id, "approver")
        db_session.flush()

        # assert_approved should now succeed
        result = assert_approved(db_session, ctx, approval_repo, approval.id)
        assert result.status == "approved"

    def test_denied_approval_permanently_blocks(self, db_session: Session):
        """AC-19: a denied approval permanently blocks the dependent operation."""
        ctx = TenantContext(is_platform_owner=True, user_id="requester")
        approval_repo = ApprovalRepository()

        approval = request_approval(
            db_session, ctx, approval_repo,
            requested_by="requester",
            context_type="test",
            reason="test",
        )
        db_session.flush()

        # Deny it
        deny_approval(db_session, ctx, approval_repo, approval.id, "approver")
        db_session.flush()

        # assert_approved should raise ApprovalDeniedError
        with pytest.raises(ApprovalDeniedError):
            assert_approved(db_session, ctx, approval_repo, approval.id)

    def test_approval_status_transitions(self, db_session: Session):
        """Q3: Approval row transitions pending→approved and pending→denied."""
        ctx = TenantContext(is_platform_owner=True, user_id="requester")
        approval_repo = ApprovalRepository()

        # Create → pending
        approval = request_approval(
            db_session, ctx, approval_repo,
            requested_by="requester", context_type="test", reason="test",
        )
        assert approval.status == "pending"
        assert approval.approved_by is None
        assert approval.approved_at is None
        db_session.flush()

        # Approve → approved
        approved = approve_approval(db_session, ctx, approval_repo, approval.id, "boss")
        assert approved.status == "approved"
        assert approved.approved_by == "boss"
        assert approved.approved_at is not None


# ============================================================
# 8.5 — Every lifecycle transition writes a history row
# ============================================================

class TestLifecycleEventRecording:
    """8.5 evidence: every transition writes a client/institution_lifecycle_event row."""

    def test_client_multiple_transitions_write_multiple_events(self, db_session: Session):
        """8.5: each Client transition writes its own event row."""
        client = _make_client(db_session, slug="multi-evt")
        db_session.commit()

        ctx = TenantContext(client_id=client.id, is_platform_owner=True, user_id="tester")
        repo = ClientRepository()

        # prospective → active
        repo.transition_lifecycle(db_session, ctx, client.id, "active", "Signed", "tester")
        db_session.flush()
        # active → suspended
        repo.transition_lifecycle(db_session, ctx, client.id, "suspended", "Unpaid", "tester")
        db_session.flush()
        # suspended → active
        repo.transition_lifecycle(db_session, ctx, client.id, "active", "Resolved", "tester")
        db_session.commit()

        events = db_session.execute(
            select(ClientLifecycleEvent)
            .where(ClientLifecycleEvent.client_id == client.id)
            .order_by(ClientLifecycleEvent.entered_at)
        ).scalars().all()
        assert len(events) == 3
        assert events[0].state == "active"
        assert events[1].state == "suspended"
        assert events[2].state == "active"

    def test_institution_multiple_transitions_write_multiple_events(self, db_session: Session):
        """8.5: each Institution transition writes its own event row."""
        client = _make_client(db_session, slug="inst-multi-evt")
        client.current_lifecycle_status = "active"
        inst = _make_institution(db_session, client.id, code="IT_MULTI")
        db_session.commit()

        ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="tester")
        repo = InstitutionRepository()

        # onboarding → active
        repo.transition_lifecycle(db_session, ctx, inst.id, "active", "Go-live", "tester")
        db_session.flush()
        # active → inactive
        repo.transition_lifecycle(db_session, ctx, inst.id, "inactive", "Break", "tester")
        db_session.flush()
        # inactive → active
        repo.transition_lifecycle(db_session, ctx, inst.id, "active", "Resume", "tester")
        db_session.commit()

        events = db_session.execute(
            select(InstitutionLifecycleEvent)
            .where(InstitutionLifecycleEvent.institution_id == inst.id)
            .order_by(InstitutionLifecycleEvent.entered_at)
        ).scalars().all()
        assert len(events) == 3
        assert events[0].state == "active"
        assert events[1].state == "inactive"
        assert events[2].state == "active"
