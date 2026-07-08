"""Tests for the repository layer (tasks 6.1–6.4, D1, A6, AC-1, AC-9).

6.1: Tenant-aware base injects client_id; repos return DTOs
6.2: institution_id default business filter + cross-institution override
6.3: OrgUnit cycle prevention (app-side, no DB trigger)
6.4: OrgUnit subtree-move semantics
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from kernel.tenant_context import TenantContext
from business.tenant_institution.models import (
    Client,
    InstitutionType,
    Institution,
    OrgUnit,
    LegalEntityType,
    InstitutionTypeName,
    OrgUnitType,
)
from business.tenant_institution.repos import (
    ClientRepository,
    InstitutionRepository,
    OrgUnitRepository,
)
from business.tenant_institution.services.dtos import (
    ClientDTO,
    InstitutionDTO,
    OrgUnitDTO,
    ClientCreateDTO,
    InstitutionCreateDTO,
    OrgUnitCreateDTO,
)


def _create_two_clients_with_institutions(db_session: Session):
    """Helper: create two clients (A, B), each with one institution and org units."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()

    client_a = Client(
        slug="school-a",
        display_name="School A",
        legal_name="School A Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoola.com",
    )
    client_b = Client(
        slug="school-b",
        display_name="School B",
        legal_name="School B Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoolb.com",
    )
    db_session.add_all([client_a, client_b])
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH_REPO", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst_a = Institution(
        client_id=client_a.id, institution_type_id=itype.id, display_name="Inst A",
    )
    inst_b = Institution(
        client_id=client_b.id, institution_type_id=itype.id, display_name="Inst B",
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    org_a1 = OrgUnit(
        client_id=client_a.id, institution_id=inst_a.id, name="Dept A1", type_id=out.id,
    )
    org_b1 = OrgUnit(
        client_id=client_b.id, institution_id=inst_b.id, name="Dept B1", type_id=out.id,
    )
    db_session.add_all([org_a1, org_b1])
    db_session.flush()

    return client_a, client_b, inst_a, inst_b, org_a1, org_b1


# ============================================================
# 6.1 — Tenant-aware base: injects client_id, returns DTOs
# ============================================================

def test_repo_list_filters_by_client_id_even_when_caller_omits_it(db_session: Session):
    """6.1 evidence: list query filters by client_id even when caller omits it (AC-1, A6)."""
    client_a, client_b, inst_a, inst_b, org_a1, org_b1 = _create_two_clients_with_institutions(db_session)
    db_session.commit()

    # Client A context — the caller does NOT pass client_id
    ctx_a = TenantContext(client_id=client_a.id, institution_id=inst_a.id, user_id="user-a")
    repo = InstitutionRepository()

    # List institutions — caller passes nothing about client_id
    results = repo.list(db_session, ctx_a)

    # Only Client A's institutions are returned (AC-1)
    result_ids = {r.id for r in results}
    assert inst_a.id in result_ids
    assert inst_b.id not in result_ids, "Client A query returned Client B data — tenant filter failed (AC-1)"


def test_repo_returns_dtos_not_orm_objects(db_session: Session):
    """6.1 evidence: repo returns DTOs, not ORM objects (tech-stack ADR §3)."""
    client_a, client_b, inst_a, inst_b, org_a1, org_b1 = _create_two_clients_with_institutions(db_session)
    db_session.commit()

    ctx_a = TenantContext(client_id=client_a.id, institution_id=inst_a.id, user_id="user-a")
    repo = InstitutionRepository()

    results = repo.list(db_session, ctx_a)
    assert len(results) > 0
    for dto in results:
        assert isinstance(dto, InstitutionDTO), f"Repo returned {type(dto)} — expected DTO (tech-stack ADR §3)"
        assert not isinstance(dto, Institution), "Repo returned ORM object — should be DTO"


def test_repo_org_unit_returns_dtos(db_session: Session):
    """6.1 evidence: OrgUnit repo returns DTOs, not ORM objects."""
    client_a, client_b, inst_a, inst_b, org_a1, org_b1 = _create_two_clients_with_institutions(db_session)
    db_session.commit()

    ctx_a = TenantContext(client_id=client_a.id, institution_id=inst_a.id, user_id="user-a")
    repo = OrgUnitRepository()

    results = repo.list(db_session, ctx_a, institution_id=inst_a.id)
    assert len(results) > 0
    for dto in results:
        assert isinstance(dto, OrgUnitDTO)
        assert not isinstance(dto, OrgUnit)


# ============================================================
# 6.2 — institution_id default business filter + cross-institution override
# ============================================================

def test_cross_institution_override_allows_director_to_read_across_institutions(db_session: Session):
    """6.2 evidence: Client Director reads across institutions within their client (D11, AC-1)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()

    client_a = Client(
        slug="multi-inst-client",
        display_name="Multi Inst Client",
        legal_name="Multi Inst Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@multi.com",
    )
    db_session.add(client_a)
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH_MULTI", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst_1 = Institution(client_id=client_a.id, institution_type_id=itype.id, display_name="Inst 1")
    inst_2 = Institution(client_id=client_a.id, institution_type_id=itype.id, display_name="Inst 2")
    db_session.add_all([inst_1, inst_2])
    db_session.commit()

    # Client Director context — no institution_id selected (cross-institution role)
    ctx_director = TenantContext(
        client_id=client_a.id, institution_id=None, user_id="director-a",
        roles=["client_director"],
    )
    repo = InstitutionRepository()

    # cross_institution=True → omits the institution_id default filter
    results = repo.list(db_session, ctx_director, cross_institution=True)
    result_ids = {r.id for r in results}
    assert inst_1.id in result_ids
    assert inst_2.id in result_ids, "Client Director should see all institutions in their client (D11)"


def test_client_a_director_cannot_read_client_b_data(db_session: Session):
    """6.2 evidence: Client-A director cannot read Client-B data (AC-1)."""
    client_a, client_b, inst_a, inst_b, org_a1, org_b1 = _create_two_clients_with_institutions(db_session)
    db_session.commit()

    # Client A director context
    ctx_a = TenantContext(
        client_id=client_a.id, institution_id=None, user_id="director-a",
        roles=["client_director"],
    )
    repo = InstitutionRepository()

    # Even with cross_institution=True, Client A director only sees Client A's institutions
    results = repo.list(db_session, ctx_a, cross_institution=True)
    result_ids = {r.id for r in results}
    assert inst_a.id in result_ids
    assert inst_b.id not in result_ids, "Client A director can see Client B data — RLS/client_id filter failed (AC-1)"


# ============================================================
# 6.3 — OrgUnit cycle prevention (app-side, no DB trigger)
# ============================================================

def test_cycle_prevention_rejects_move_under_descendant(db_session: Session):
    """6.3 evidence: moving a node under its own descendant is rejected (AC-9, Q6)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()

    client = Client(
        slug="cycle-test", display_name="Cycle Test", legal_name="Cycle Test Ltd",
        legal_entity_type_id=let.id, primary_contact_email="i@cycletest.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH_CYC", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(client_id=client.id, institution_type_id=itype.id, display_name="Cycle Inst")
    db_session.add(inst)
    db_session.flush()

    # Create A → B → C (A is parent of B, B is parent of C)
    node_a = OrgUnit(client_id=client.id, institution_id=inst.id, name="A", type_id=out.id)
    db_session.add(node_a)
    db_session.flush()
    node_b = OrgUnit(client_id=client.id, institution_id=inst.id, parent_id=node_a.id, name="B", type_id=out.id)
    db_session.add(node_b)
    db_session.flush()
    node_c = OrgUnit(client_id=client.id, institution_id=inst.id, parent_id=node_b.id, name="C", type_id=out.id)
    db_session.add(node_c)
    db_session.flush()
    db_session.commit()

    ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="admin")
    repo = OrgUnitRepository()

    # Attempt to move A under C (C is A's descendant) — must be rejected
    with pytest.raises(ValueError, match="[Cc]ycle"):
        repo.move(db_session, ctx, node_a.id, node_c.id)


def test_no_db_trigger_for_cycle_prevention(db_engine):
    """6.3 evidence: schema inspection asserts NO DB trigger exists for cycle prevention (Q6, AC-9)."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tg.tgname, tg.tgtype
            FROM pg_trigger tg
            JOIN pg_class cls ON tg.tgrelid = cls.oid
            WHERE cls.relname = 'org_unit'
              AND NOT tg.tgisinternal
        """))
        triggers = result.fetchall()
        assert len(triggers) == 0, (
            f"DB trigger(s) found on org_unit table — cycle prevention must be app-side only (Q6): "
            f"{[t[0] for t in triggers]}"
        )


# ============================================================
# 6.4 — OrgUnit subtree-move semantics
# ============================================================

def test_subtree_move_retains_descendant_structure(db_session: Session):
    """6.4 evidence: moving a subtree retains descendants' relative structure (AC-9)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()

    client = Client(
        slug="subtree-test", display_name="Subtree Test", legal_name="Subtree Ltd",
        legal_entity_type_id=let.id, primary_contact_email="i@subtree.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH_SUB", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(client_id=client.id, institution_type_id=itype.id, display_name="Subtree Inst")
    db_session.add(inst)
    db_session.flush()

    # Build: root1 → A → B, root2 (standalone)
    root1 = OrgUnit(client_id=client.id, institution_id=inst.id, name="root1", type_id=out.id)
    root2 = OrgUnit(client_id=client.id, institution_id=inst.id, name="root2", type_id=out.id)
    db_session.add_all([root1, root2])
    db_session.flush()

    node_a = OrgUnit(client_id=client.id, institution_id=inst.id, parent_id=root1.id, name="A", type_id=out.id)
    db_session.add(node_a)
    db_session.flush()
    node_b = OrgUnit(client_id=client.id, institution_id=inst.id, parent_id=node_a.id, name="B", type_id=out.id)
    db_session.add(node_b)
    db_session.flush()
    db_session.commit()

    ctx = TenantContext(client_id=client.id, institution_id=inst.id, user_id="admin")
    repo = OrgUnitRepository()

    # Move A (with descendant B) to under root2
    repo.move(db_session, ctx, node_a.id, root2.id)
    db_session.commit()

    # Verify A is now under root2
    moved_a = repo._get_orm_by_id(db_session, node_a.id)
    assert moved_a.parent_id == root2.id, "A should be under root2 after move"

    # Verify B is still under A (relative structure preserved)
    moved_b = repo._get_orm_by_id(db_session, node_b.id)
    assert moved_b.parent_id == node_a.id, "B should still be under A after subtree move (AC-9)"

    # Verify A is no longer under root1
    assert moved_a.parent_id != root1.id
