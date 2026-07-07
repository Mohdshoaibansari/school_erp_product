"""Tests for OrgUnit hierarchy + move (tasks 9.1–9.4).

9.1: OrgUnit archive-only deletion + reactivation; NO hard-delete path
9.2: OrgUnit type immutability after creation
9.3: Recursive CTE subtree/ancestor queries
9.4: OrgUnit move with cycle-prevention + subtree moves + audit (AC-10 placeholder)
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from kernel.tenant_institution.models import (
    Client,
    Institution,
    InstitutionType,
    LegalEntityType,
    InstitutionTypeName,
    OrgUnitType,
    OrgUnit,
)
from kernel.tenant_institution.repos import OrgUnitRepository
from kernel.tenant_institution.services.dtos import OrgUnitDTO


# ============================================================
# Helpers
# ============================================================

def _get_lookup_ids(db_session: Session):
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()
    return let.id, itn.id, out.id


def _setup_tree(db_session: Session, slug: str = "ou-test") -> tuple:
    """Create a client + institution + 3-level OrgUnit tree (A → B → C)."""
    let_id, itn_id, out_id = _get_lookup_ids(db_session)

    client = Client(
        slug=slug, display_name=slug.title(), legal_name=f"{slug} Ltd",
        legal_entity_type_id=let_id, primary_contact_email=f"i@{slug}.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(name_id=itn_id, code=f"IT_{slug.upper()}", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(
        client_id=client.id, institution_type_id=itype.id, display_name=f"{slug} Inst",
    )
    db_session.add(inst)
    db_session.flush()

    node_a = OrgUnit(client_id=client.id, institution_id=inst.id, name="A", type_id=out_id)
    db_session.add(node_a)
    db_session.flush()
    node_b = OrgUnit(
        client_id=client.id, institution_id=inst.id, parent_id=node_a.id, name="B", type_id=out_id,
    )
    db_session.add(node_b)
    db_session.flush()
    node_c = OrgUnit(
        client_id=client.id, institution_id=inst.id, parent_id=node_b.id, name="C", type_id=out_id,
    )
    db_session.add(node_c)
    db_session.flush()
    db_session.commit()

    ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="admin")
    return ctx, client, inst, node_a, node_b, node_c


# ============================================================
# 9.1 — OrgUnit archive-only deletion + reactivation (AC-8)
# ============================================================

class TestOrgUnitArchiveOnly:
    """9.1 evidence: archive-only deletion + reactivation; NO hard-delete path."""

    def test_archive_soft_deletes_to_archived(self, db_session: Session):
        """AC-8: 'delete' archives (soft-delete), not hard-delete."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="arch-ou")
        repo = OrgUnitRepository()

        result = repo.archive(db_session, ctx, node_a.id)
        db_session.commit()

        assert result.current_lifecycle_status == "archived"
        assert result.archived_at is not None

    def test_reactivation_restores_active(self, db_session: Session):
        """AC-8: reactivation restores active state."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="react-ou")
        repo = OrgUnitRepository()

        repo.archive(db_session, ctx, node_a.id)
        db_session.flush()
        result = repo.reactivate(db_session, ctx, node_a.id)
        db_session.commit()

        assert result.current_lifecycle_status == "active"
        assert result.archived_at is None

    def test_no_hard_delete_path_exists(self, db_session: Session):
        """AC-8: no hard-delete method exists on the repository."""
        repo = OrgUnitRepository()
        # The repository must NOT have a delete/hard_delete method
        assert not hasattr(repo, "delete"), \
            "OrgUnitRepository must NOT have a 'delete' method (archive-only, AC-8)"
        assert not hasattr(repo, "hard_delete"), \
            "OrgUnitRepository must NOT have a 'hard_delete' method (archive-only, AC-8)"

    def test_archived_org_unit_still_exists_in_db(self, db_session: Session):
        """AC-8: archived OrgUnit row still exists (not hard-deleted)."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="exists-ou")
        repo = OrgUnitRepository()

        repo.archive(db_session, ctx, node_a.id)
        db_session.commit()

        # The row still exists in the DB
        db_session.expire_all()
        row = db_session.execute(
            select(OrgUnit).where(OrgUnit.id == node_a.id)
        ).scalars().first()
        assert row is not None, "Archived OrgUnit row must still exist (no hard-delete, AC-8)"
        assert row.current_lifecycle_status == "archived"


# ============================================================
# 9.2 — OrgUnit type immutability after creation (AC-8)
# ============================================================

class TestOrgUnitTypeImmutability:
    """9.2 evidence: OrgUnit type is immutable after creation."""

    def test_update_type_rejected(self, db_session: Session):
        """AC-8: updating type is rejected."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="imm-ou")
        repo = OrgUnitRepository()

        # Get a different OrgUnitType
        types = db_session.query(OrgUnitType).all()
        other_type = types[1] if len(types) > 1 else types[0]

        with pytest.raises(ValueError, match="immutable"):
            repo.update_type(db_session, ctx, node_a.id, other_type.id)

    def test_update_identity_does_not_accept_type(self, db_session: Session):
        """AC-8: update_identity method does NOT accept a type_id parameter."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="imm2-ou")
        repo = OrgUnitRepository()

        # update_identity accepts name, code, sort_order — NOT type_id
        result = repo.update_identity(db_session, ctx, node_a.id, name="Renamed")
        assert result.name == "Renamed"
        # type_id is unchanged
        assert result.type_id == node_a.type_id


# ============================================================
# 9.3 — Recursive CTE subtree/ancestor queries (D6)
# ============================================================

class TestRecursiveCTE:
    """9.3 evidence: recursive CTE subtree/ancestor queries."""

    def test_subtree_returns_all_descendants(self, db_session: Session):
        """D6: subtree query returns the full subtree of a node."""
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="cte-sub")
        repo = OrgUnitRepository()

        subtree = repo.get_subtree(db_session, ctx, node_a.id)
        subtree_ids = {s.id for s in subtree}
        # Should include A, B, C
        assert node_a.id in subtree_ids
        assert node_b.id in subtree_ids
        assert node_c.id in subtree_ids
        assert len(subtree) == 3

    def test_subtree_of_leaf_returns_only_self(self, db_session: Session):
        """D6: subtree of a leaf node returns only itself."""
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="cte-leaf")
        repo = OrgUnitRepository()

        subtree = repo.get_subtree(db_session, ctx, node_c.id)
        assert len(subtree) == 1
        assert subtree[0].id == node_c.id

    def test_ancestors_returns_full_chain(self, db_session: Session):
        """D6: ancestors query returns the full ancestor chain (nearest to root)."""
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="cte-anc")
        repo = OrgUnitRepository()

        ancestors = repo.get_ancestors(db_session, ctx, node_c.id)
        ancestor_ids = [a.id for a in ancestors]
        # Should be [B, A] (nearest parent first, then root)
        assert node_b.id in ancestor_ids
        assert node_a.id in ancestor_ids
        assert node_c.id not in ancestor_ids
        assert len(ancestors) == 2
        # B should come before A (nearest first)
        assert ancestor_ids.index(node_b.id) < ancestor_ids.index(node_a.id)

    def test_ancestors_of_root_returns_empty(self, db_session: Session):
        """D6: ancestors of a root node returns empty list."""
        ctx, client, inst, node_a, _, _ = _setup_tree(db_session, slug="cte-root")
        repo = OrgUnitRepository()

        ancestors = repo.get_ancestors(db_session, ctx, node_a.id)
        assert len(ancestors) == 0


# ============================================================
# 9.4 — OrgUnit move with cycle-prevention + subtree + audit (AC-9, AC-10)
# ============================================================

class TestOrgUnitMove:
    """9.4 evidence: move with cycle-prevention + subtree + audit placeholder."""

    def test_cycle_prevented_on_move(self, db_session: Session):
        """AC-9: moving a node under its own descendant is rejected."""
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="cyc-move")
        repo = OrgUnitRepository()

        # Move A under C (C is A's descendant) — must be rejected
        with pytest.raises(ValueError, match="[Cc]ycle"):
            repo.move(db_session, ctx, node_a.id, node_c.id)

    def test_subtree_moves_with_node(self, db_session: Session):
        """AC-9: moving a node moves the entire subtree (relative structure preserved)."""
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="sub-move")

        # Create a new root to move under
        out_id = _get_lookup_ids(db_session)[2]
        new_root = OrgUnit(
            client_id=client.id, institution_id=inst.id, name="new_root", type_id=out_id,
        )
        db_session.add(new_root)
        db_session.flush()
        db_session.commit()

        repo = OrgUnitRepository()
        # Move B (with descendant C) under new_root
        repo.move(db_session, ctx, node_b.id, new_root.id)
        db_session.commit()

        # B should now be under new_root
        moved_b = repo._get_orm_by_id(db_session, node_b.id)
        assert moved_b.parent_id == new_root.id

        # C should still be under B (relative structure preserved)
        moved_c = repo._get_orm_by_id(db_session, node_c.id)
        assert moved_c.parent_id == node_b.id

    def test_no_dedicated_org_unit_move_event_table(self, db_engine):
        """AC-10, Q7: NO dedicated org_unit_move_event table exists."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'org_unit_move_event'
            """))
            tables = result.fetchall()
            assert len(tables) == 0, (
                "A dedicated 'org_unit_move_event' table exists — "
                "Q7 requires NO dedicated table (generic C-11 audit event only)"
            )

    def test_move_emits_audit_event_via_emitter(self, db_session: Session):
        """AC-10, 13.3: move emits a C-11 audit event via the AuditEmitter.

        Apply-C emitted a placeholder structured log; Apply-D (task 13.3)
        replaces it with the real synchronous C-11 emitter call. The emitter
        is called with ``action="org_unit_moved"`` and a payload carrying
        ``{from_parent, to_parent, moved_by, ...}`` (Q7).
        """
        ctx, client, inst, node_a, node_b, node_c = _setup_tree(db_session, slug="audit-move")

        # Create a new root
        out_id = _get_lookup_ids(db_session)[2]
        new_root = OrgUnit(
            client_id=client.id, institution_id=inst.id, name="audit_root", type_id=out_id,
        )
        db_session.add(new_root)
        db_session.flush()
        db_session.commit()

        # Inject a capture emitter so we can assert the payload
        from kernel.tenant_institution.services.audit import DefaultAuditEmitter
        emitter = DefaultAuditEmitter()
        repo = OrgUnitRepository(audit_emitter=emitter)
        repo.move(db_session, ctx, node_a.id, new_root.id)
        db_session.commit()

        moved_events = [e for e in emitter.events if e["action"] == "org_unit_moved"]
        assert len(moved_events) == 1, (
            "Move should emit exactly one 'org_unit_moved' C-11 audit event (AC-10, 13.3)"
        )
        evt = moved_events[0]
        assert evt["client_id"] == client.id
        assert evt["institution_id"] == inst.id
        payload = evt["payload"]
        assert payload["org_unit_id"] == str(node_a.id)
        assert payload["from_parent"] == str(node_a.parent_id) or payload["from_parent"] is None
        assert payload["to_parent"] == str(new_root.id)
        assert payload["moved_by"] == ctx.user_id
