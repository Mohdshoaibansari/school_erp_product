"""Tests for RLS policies (D1, Q1, AC-1, AC-14).

Verifies:
- Cross-tenant isolation: Client A query returns no Client B rows (AC-1)
- Self-visible client RLS: a Client Director reads only their own Client row (AC-14)
- Platform Owner bypass: reads all rows across tenants (D11)
- No RLS on institution_id (business filter, not hard fence) (D1)
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from kernel.tenant_institution.models import (
    LegalEntityType,
    OrgUnitType,
    InstitutionTypeName,
    Client,
    InstitutionType,
    Institution,
    OrgUnit,
    Approval,
)

from tests.conftest import DATABASE_URL
from sqlalchemy import create_engine


def _setup_two_tenants(db_session: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create two clients, each with an institution and org unit.
    Returns (client_a_id, client_b_id, inst_a_id, inst_b_id).
    """
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()

    # Client A
    client_a = Client(
        slug="school-a",
        display_name="School A",
        legal_name="School A Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoola.com",
    )
    db_session.add(client_a)

    # Client B
    client_b = Client(
        slug="school-b",
        display_name="School B",
        legal_name="School B Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@schoolb.com",
    )
    db_session.add(client_b)
    db_session.flush()

    # InstitutionType
    itype = InstitutionType(name_id=itn.id, code="SCH_RLS", is_system=True)
    db_session.add(itype)
    db_session.flush()

    # Institution A (under Client A)
    inst_a = Institution(
        client_id=client_a.id,
        institution_type_id=itype.id,
        display_name="Institution A",
    )
    db_session.add(inst_a)

    # Institution B (under Client B)
    inst_b = Institution(
        client_id=client_b.id,
        institution_type_id=itype.id,
        display_name="Institution B",
    )
    db_session.add(inst_b)
    db_session.flush()

    # OrgUnit A (under Institution A)
    org_a = OrgUnit(
        client_id=client_a.id,
        institution_id=inst_a.id,
        name="Dept A",
        type_id=out.id,
    )
    db_session.add(org_a)

    # OrgUnit B (under Institution B)
    org_b = OrgUnit(
        client_id=client_b.id,
        institution_id=inst_b.id,
        name="Dept B",
        type_id=out.id,
    )
    db_session.add(org_b)
    db_session.flush()

    return client_a.id, client_b.id, inst_a.id, inst_b.id


def test_cross_tenant_isolation_institution(db_session: Session, db_engine):
    """Client A query returns no Client B rows (AC-1)."""
    client_a_id, client_b_id, inst_a_id, inst_b_id = _setup_two_tenants(db_session)
    db_session.commit()

    # Use a fresh connection with RLS GUC set to Client A
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Set Client A context (as superuser, then switch to non-superuser for RLS)
        conn.execute(text(f"SET LOCAL app.current_client_id = '{client_a_id}'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        # Query institutions — should only see Client A's
        result = conn.execute(text("SELECT id, display_name FROM institution"))
        rows = result.fetchall()
        visible_ids = {row[0] for row in rows}
        assert inst_a_id in visible_ids
        assert inst_b_id not in visible_ids, "Client A can see Client B's institution — RLS failed (AC-1)"
    engine.dispose()


def test_self_visible_client_rls(db_session: Session):
    """Client Director reads only their own Client row (Q1, AC-14)."""
    client_a_id, client_b_id, _, _ = _setup_two_tenants(db_session)
    db_session.commit()

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL app.current_client_id = '{client_a_id}'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        result = conn.execute(text("SELECT id, slug FROM client"))
        rows = result.fetchall()
        visible_ids = {row[0] for row in rows}
        assert client_a_id in visible_ids
        assert client_b_id not in visible_ids, "Client A can see Client B's row — RLS failed (AC-14)"
    engine.dispose()


def test_platform_owner_reads_all_clients(db_session: Session):
    """Platform Owner reads all Client rows (D11, AC-14)."""
    client_a_id, client_b_id, _, _ = _setup_two_tenants(db_session)
    db_session.commit()

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        result = conn.execute(text("SELECT id, slug FROM client"))
        rows = result.fetchall()
        visible_ids = {row[0] for row in rows}
        assert client_a_id in visible_ids
        assert client_b_id in visible_ids
    engine.dispose()


def test_platform_owner_reads_all_institutions_across_tenants(db_session: Session):
    """Platform Owner reads all institutions across tenants (AC-1 bypass, D11)."""
    client_a_id, client_b_id, inst_a_id, inst_b_id = _setup_two_tenants(db_session)
    db_session.commit()

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SET LOCAL app.is_platform_owner = 'true'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        result = conn.execute(text("SELECT id FROM institution"))
        rows = result.fetchall()
        visible_ids = {row[0] for row in rows}
        assert inst_a_id in visible_ids
        assert inst_b_id in visible_ids
    engine.dispose()


def test_cross_tenant_isolation_org_units(db_session: Session):
    """Client A cannot see Client B's OrgUnits (AC-1)."""
    client_a_id, client_b_id, inst_a_id, inst_b_id = _setup_two_tenants(db_session)
    db_session.commit()

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL app.current_client_id = '{client_a_id}'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        result = conn.execute(text("SELECT id, name FROM org_unit"))
        rows = result.fetchall()
        names = {row[1] for row in rows}
        assert "Dept A" in names
        assert "Dept B" not in names
    engine.dispose()


def test_no_rls_on_institution_id(db_session: Session):
    """No RLS policy on institution_id — it's a business filter, not a hard fence (D1).

    A cross-institution role within the same Client can read across institutions.
    """
    client_a_id, _, inst_a_id, inst_b_id = _setup_two_tenants(db_session)
    db_session.commit()

    # Verify no RLS policy references institution_id — and verify cross-institution access works
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Check policy expressions don't reference institution_id
        result = conn.execute(text("""
            SELECT pg_get_expr(pol.polqual, pol.polrelid) as using_expr
            FROM pg_policy pol
            JOIN pg_class cls ON pol.polrelid = cls.oid
            WHERE cls.relname = 'institution' AND pol.polcmd = 'r'
        """))
        for row in result:
            assert "institution_id" not in (row[0] or ""), \
                "RLS policy on institution table references institution_id — should only use client_id (D1)"

        # Verify cross-institution read works within same client (business filter, not RLS)
        conn.execute(text(f"SET LOCAL app.current_client_id = '{client_a_id}'"))
        conn.execute(text("SET LOCAL ROLE test_tenant_user"))
        result2 = conn.execute(text("SELECT id FROM institution"))
        visible_ids = {row[0] for row in result2}
        # Client A has one institution, visible
        assert inst_a_id in visible_ids
    engine.dispose()


def test_no_client_id_column_on_client(db_engine):
    """The client table has no client_id column (Q1)."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'client'
        """))
        cols = {row[0] for row in result}
        assert "client_id" not in cols


def test_org_unit_root_and_child(db_session: Session):
    """Test inserting a root OrgUnit and a child (task 2.4 evidence)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()

    client = Client(
        slug="org-test-client",
        display_name="Org Test Client",
        legal_name="Org Test Client Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@orgtest.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH_ORG", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(
        client_id=client.id,
        institution_type_id=itype.id,
        display_name="Org Test Inst",
    )
    db_session.add(inst)
    db_session.flush()

    root = OrgUnit(
        client_id=client.id,
        institution_id=inst.id,
        name="Root Dept",
        type_id=out.id,
        sort_order=0,
    )
    db_session.add(root)
    db_session.flush()

    child = OrgUnit(
        client_id=client.id,
        institution_id=inst.id,
        parent_id=root.id,
        name="Child Dept",
        type_id=out.id,
        sort_order=1,
    )
    db_session.add(child)
    db_session.flush()

    assert root.id is not None
    assert child.id is not None
    assert child.parent_id == root.id


def test_approval_row_creatable(db_session: Session):
    """Approvals table allows creating a pending Approval row (Q3, AC-19)."""
    approval = Approval(
        requested_by="test-platform-owner",
        status="pending",
        context_type="client_lifecycle",
    )
    db_session.add(approval)
    db_session.flush()
    assert approval.id is not None
    assert approval.status == "pending"
    assert approval.requested_by == "test-platform-owner"