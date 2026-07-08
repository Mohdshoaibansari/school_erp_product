"""Tests for synchronous C-11 audit emission (tasks 13.1–13.5).

C-11 (Audit) is a BOUNDARY — C-11 owns the audit log. C-01 implements a
synchronous AuditEmitter Protocol + a default capture implementation
(no message broker — Q4 deferred, 13.5). The emitter is wired into:
- 13.1: Client lifecycle transitions (ClientId tagged, AC-5)
- 13.2: Institution lifecycle transitions (ClientId + InstitutionId, AC-6)
- 13.3: OrgUnit moves (generic action="org_unit_moved", Q7, AC-10)
- 13.4: ownership transfer + the immutability invariant (AC-11)
- 13.5: no message broker / async event bus (Q4)
plus 12.3: all C-01 writes record actor identity via C-11 (AC-15).
"""

from __future__ import annotations

import uuid
from sqlalchemy import text
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
)
from business.tenant_institution.repos import (
    ClientRepository,
    InstitutionRepository,
    OrgUnitRepository,
    OwnershipTransferRepository,
)
from kernel.audit import (
    AuditEmitter,
    DefaultAuditEmitter,
)


# ============================================================
# Helpers
# ============================================================

def _get_lookup_ids(db_session: Session):
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()
    return let.id, itn.id, out.id


def _make_client(db_session: Session, slug: str = "aud-client", status: str = "prospective") -> Client:
    let_id, _, _ = _get_lookup_ids(db_session)
    client = Client(
        slug=slug, display_name=slug.title(), legal_name=f"{slug} Ltd",
        legal_entity_type_id=let_id, primary_contact_email=f"i@{slug}.com",
        current_lifecycle_status=status,
    )
    db_session.add(client)
    db_session.flush()
    return client


def _make_institution(db_session: Session, client_id: uuid.UUID, code: str = "IT_AUD") -> Institution:
    _, itn_id, _ = _get_lookup_ids(db_session)
    itype = InstitutionType(name_id=itn_id, code=code, is_system=True)
    db_session.add(itype)
    db_session.flush()
    inst = Institution(
        client_id=client_id, institution_type_id=itype.id, display_name=f"{code} Inst",
        current_lifecycle_status="onboarding",
    )
    db_session.add(inst)
    db_session.flush()
    return inst


# ============================================================
# 13.1 — Client lifecycle transitions emit C-11 audit (AC-5)
# ============================================================

class TestClientLifecycleAudit:
    """13.1: synchronous C-11 audit emission for Client lifecycle transitions."""

    def test_transition_emits_audit_event_with_client_id(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = ClientRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="cl-aud", status="prospective")
        ctx = TenantContext(is_platform_owner=True, roles=["platform_owner"], user_id="po-1")

        repo.transition_lifecycle(db_session, ctx, client.id, "active", reason="go-live", actor="po-1")
        db_session.commit()

        events = [e for e in emitter.events if e["action"] == "client_lifecycle_transition"]
        assert len(events) == 1
        evt = events[0]
        assert evt["client_id"] == client.id
        assert evt["institution_id"] is None
        assert evt["actor"] == "po-1"
        # payload carries transition provenance (AC-5)
        assert evt["payload"]["from_state"] == "prospective"
        assert evt["payload"]["to_state"] == "active"
        assert evt["payload"]["reason"] == "go-live"

    def test_emitter_is_synchronous_no_broker(self):
        """13.5: the default emitter is synchronous (capture list, in-process)."""
        emitter = DefaultAuditEmitter()
        cid = uuid.uuid4()
        emitter.emit(action="client_lifecycle_transition", client_id=cid, actor="po-1")
        assert len(emitter.events) == 1  # captured synchronously, no queue/broker


# ============================================================
# 13.2 — Institution lifecycle transitions emit C-11 audit (AC-6)
# ============================================================

class TestInstitutionLifecycleAudit:
    """13.2: synchronous C-11 audit emission for Institution lifecycle transitions."""

    def test_transition_emits_audit_event_client_and_institution_id(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = InstitutionRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="ins-aud", status="active")
        inst = _make_institution(db_session, client.id, code="IT_INS_AUD")
        ctx = TenantContext(
            client_id=client.id, is_platform_owner=False, roles=["client_director"],
            user_id="cd-1",
        )

        repo.transition_lifecycle(db_session, ctx, inst.id, "active", reason="go-live", actor="cd-1")
        db_session.commit()

        events = [e for e in emitter.events if e["action"] == "institution_lifecycle_transition"]
        assert len(events) == 1
        evt = events[0]
        # AC-6: tagged with ClientId + InstitutionId
        assert evt["client_id"] == client.id
        assert evt["institution_id"] == inst.id
        assert evt["actor"] == "cd-1"
        assert evt["payload"]["from_state"] == "onboarding"
        assert evt["payload"]["to_state"] == "active"


# ============================================================
# 13.3 — OrgUnit moves emit C-11 audit (AC-10, Q7)
# ============================================================

class TestOrgUnitMoveAudit:
    """13.3: C-11 audit emission for OrgUnit moves; no dedicated table (Q7)."""

    def test_move_emits_org_unit_moved_event_payload(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = OrgUnitRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="ou-aud", status="active")
        inst = _make_institution(db_session, client.id, code="IT_OU_AUD")
        out_id = _get_lookup_ids(db_session)[2]
        root = OrgUnit(
            client_id=client.id, institution_id=inst.id, name="root", type_id=out_id,
        )
        db_session.add(root)
        db_session.flush()  # root.id is now populated
        child = OrgUnit(
            client_id=client.id, institution_id=inst.id, name="child", type_id=out_id,
            parent_id=root.id,
        )
        db_session.add(child)
        db_session.flush()
        db_session.commit()

        new_parent = OrgUnit(
            client_id=client.id, institution_id=inst.id, name="new_root", type_id=out_id,
        )
        db_session.add(new_parent)
        db_session.flush()
        db_session.commit()

        ctx = TenantContext(
            client_id=client.id, is_platform_owner=False, roles=["institution_admin"],
            user_id="ia-1",
        )
        repo.move(db_session, ctx, child.id, new_parent.id)
        db_session.commit()

        events = [e for e in emitter.events if e["action"] == "org_unit_moved"]
        assert len(events) == 1
        evt = events[0]
        assert evt["client_id"] == client.id
        assert evt["institution_id"] == inst.id
        payload = evt["payload"]
        assert payload["org_unit_id"] == str(child.id)
        assert payload["from_parent"] == str(root.id)
        assert payload["to_parent"] == str(new_parent.id)
        assert payload["moved_by"] == "ia-1"

    def test_no_dedicated_org_unit_move_event_table(self, db_engine):
        """Q7: NO dedicated org_unit_move_event table — generic C-11 event only."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'org_unit_move_event'
            """))
            assert result.fetchall() == []


# ============================================================
# 13.4 — ownership transfer emits C-11 audit + immutability invariant (AC-11)
# ============================================================

class TestOwnershipTransferAudit:
    """13.4: C-11 audit emission for ownership transfer + immutability invariant."""

    def test_transfer_emits_ownership_transferred_audit_event(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        transfer_repo = OwnershipTransferRepository(audit_emitter=emitter)

        client_a = _make_client(db_session, slug="xfer-aud-a", status="active")
        client_b = _make_client(db_session, slug="xfer-aud-b", status="active")
        inst = _make_institution(db_session, client_a.id, code="IT_XFER_AUD")
        db_session.commit()

        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, roles=["platform_owner"], user_id="po-1")
        approval = transfer_repo.request_transfer(
            db_session, ctx, inst.id, client_b.id, reason="transfer",
        )
        db_session.commit()

        # Pre-transfer audit event recorded under original ClientId (client_a)
        emitter.emit(
            action="client_lifecycle_transition", client_id=client_a.id, actor="po-1",
        )
        pre_transfer_events = list(emitter.events)

        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id, consent_source=True, consent_dest=True,
            reason="transfer",
        )
        db_session.commit()

        transfer_events = [e for e in emitter.events if e["action"] == "ownership_transferred"]
        assert len(transfer_events) == 1
        evt = transfer_events[0]
        assert evt["actor"] == "po-1"
        assert evt["payload"]["from_client_id"] == str(client_a.id)
        assert evt["payload"]["to_client_id"] == str(client_b.id)
        assert evt["payload"]["institution_id"] == str(inst.id)
        assert evt["payload"]["consent_source"] is True
        assert evt["payload"]["consent_dest"] is True

    def test_immutability_invariant_pre_transfer_events_keep_original_clientid(self, db_session: Session):
        """13.4 / 11.5: pre-transfer audit events keep their original ClientId; the
        transfer does NOT rewrite them (D12, ADR §5 constraint 14)."""
        emitter = DefaultAuditEmitter()
        transfer_repo = OwnershipTransferRepository(audit_emitter=emitter)

        client_a = _make_client(db_session, slug="imm-aud-a", status="active")
        client_b = _make_client(db_session, slug="imm-aud-b", status="active")
        inst = _make_institution(db_session, client_a.id, code="IT_IMM_AUD")
        db_session.commit()

        ctx = TenantContext(client_id=client_a.id, is_platform_owner=True, roles=["platform_owner"], user_id="po-1")
        approval = transfer_repo.request_transfer(
            db_session, ctx, inst.id, client_b.id, reason="transfer",
        )
        db_session.commit()

        # Emit a pre-transfer audit event tagged with the ORIGINAL ClientId (client_a)
        emitter.emit(
            action="client_lifecycle_transition",
            client_id=client_a.id, actor="po-1",
            payload={"label": "pre-transfer"},
        )
        pre_transfer_client_id = emitter.events[-1]["client_id"]

        transfer_repo.approve_transfer(
            db_session, ctx, approval.id, inst.id,
            client_a.id, client_b.id, consent_source=True, consent_dest=True,
            reason="transfer",
        )
        db_session.commit()

        # The pre-transfer event's ClientId was NOT rewritten to client_b
        assert pre_transfer_client_id == client_a.id
        assert emitter.events[0]["client_id"] == client_a.id
        # The transfer audit event is tagged with the new owner (client_b)
        transfer_evt = next(e for e in emitter.events if e["action"] == "ownership_transferred")
        assert transfer_evt["client_id"] == client_b.id
        # No existing event had its client_id mutated (list is append-only)
        assert all(
            e["client_id"] != client_b.id
            for e in emitter.events
            if e["action"] != "ownership_transferred"
        ), "Transfer MUST NOT rewrite pre-existing audit-event ClientIds (immutability invariant, AC-11)"


# ============================================================
# 13.5 — no message broker / async event bus (Q4)
# ============================================================

class TestNoMessageBroker:
    """13.5: confirm no message broker / async event bus is introduced for C-01 (Q4)."""

    def test_audit_emitter_is_synchronous_protocol(self):
        """The AuditEmitter protocol has a single synchronous emit() — no async/await."""
        import inspect

        assert hasattr(AuditEmitter, "emit")
        sig = inspect.signature(AuditEmitter.emit) if hasattr(AuditEmitter, "emit") else None
        # DefaultAuditEmitter.emit must NOT be a coroutine function
        assert not inspect.iscoroutinefunction(DefaultAuditEmitter.emit)

    def test_no_broker_imports_in_c01_source(self):
        """13.5: assert no pika/kafka/redis/celery broker imports in C-01 source."""
        import ast
        import pathlib

        broker_modules = {"pika", "kafka", "redis", "celery", "aio_pika", "aiokafka"}
        c01_root = pathlib.Path("business/tenant_institution")
        violations = []
        for py in c01_root.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        root = n.name.split(".")[0]
                        if root in broker_modules:
                            violations.append(f"{py}: import {n.name}")
                elif isinstance(node, ast.ImportFrom):
                    root = (node.module or "").split(".")[0]
                    if root in broker_modules:
                        violations.append(f"{py}: from {node.module} import ...")
        assert violations == [], f"Broker imports forbidden for C-01 (Q4): {violations}"


# ============================================================
# 12.3 — all C-01 writes record actor identity via C-11 (AC-15)
# ============================================================

class TestAllWritesRecordActor:
    """12.3: every C-01 write records actor identity via the C-11 audit emitter."""

    def test_client_transition_records_actor(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = ClientRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="act-cl", status="prospective")
        ctx = TenantContext(is_platform_owner=True, roles=["platform_owner"], user_id="actor-x")
        repo.transition_lifecycle(db_session, ctx, client.id, "active", reason="go", actor="actor-x")
        evt = next(e for e in emitter.events if e["action"] == "client_lifecycle_transition")
        assert evt["actor"] == "actor-x"

    def test_institution_transition_records_actor(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = InstitutionRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="act-ins", status="active")
        inst = _make_institution(db_session, client.id, code="IT_ACT_INS")
        ctx = TenantContext(client_id=client.id, roles=["client_director"], user_id="actor-y")
        repo.transition_lifecycle(db_session, ctx, inst.id, "active", reason="go", actor="actor-y")
        evt = next(e for e in emitter.events if e["action"] == "institution_lifecycle_transition")
        assert evt["actor"] == "actor-y"

    def test_orgunit_move_records_actor(self, db_session: Session):
        emitter = DefaultAuditEmitter()
        repo = OrgUnitRepository(audit_emitter=emitter)
        client = _make_client(db_session, slug="act-ou", status="active")
        inst = _make_institution(db_session, client.id, code="IT_ACT_OU")
        out_id = _get_lookup_ids(db_session)[2]
        ou = OrgUnit(client_id=client.id, institution_id=inst.id, name="n", type_id=out_id)
        db_session.add(ou)
        db_session.flush()
        new_root = OrgUnit(client_id=client.id, institution_id=inst.id, name="r", type_id=out_id)
        db_session.add(new_root)
        db_session.flush()
        db_session.commit()
        ctx = TenantContext(client_id=client.id, roles=["institution_admin"], user_id="actor-z")
        repo.move(db_session, ctx, ou.id, new_root.id)
        evt = next(e for e in emitter.events if e["action"] == "org_unit_moved")
        assert evt["actor"] == "actor-z"