"""Tests for UUID v4 primary keys on all C-01 entities (AC-2).

Verifies: UUID v4 PKs, no autoincrement sequences.
"""

from __future__ import annotations

import uuid

from sqlalchemy import create_engine, text
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
    ClientLifecycleEvent,
    InstitutionLifecycleEvent,
    OwnershipTransferEvent,
)

from tests.conftest import DATABASE_URL


def test_client_pk_is_uuid_v4(db_session: Session):
    """Client PK is a UUID v4 (AC-2)."""
    # Get a legal entity type from seed data
    let = db_session.query(LegalEntityType).first()
    assert let is not None

    client = Client(
        slug="test-school-a",
        display_name="Test School A",
        legal_name="Test School A Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@testschoola.com",
    )
    db_session.add(client)
    db_session.flush()
    assert client.id is not None
    assert isinstance(client.id, uuid.UUID)
    assert client.id.version == 4  # UUID v4


def test_institution_pk_is_uuid_v4(db_session: Session):
    """Institution PK is a UUID v4 (AC-2)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    client = Client(
        slug="test-inst-client",
        display_name="Test Inst Client",
        legal_name="Test Inst Client Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@testinstclient.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(
        name_id=itn.id,
        code="SCH",
        is_system=True,
    )
    db_session.add(itype)
    db_session.flush()

    inst = Institution(
        client_id=client.id,
        institution_type_id=itype.id,
        display_name="Test Institution",
    )
    db_session.add(inst)
    db_session.flush()
    assert isinstance(inst.id, uuid.UUID)
    assert inst.id.version == 4


def test_org_unit_pk_is_uuid_v4(db_session: Session):
    """OrgUnit PK is a UUID v4 (AC-2)."""
    let = db_session.query(LegalEntityType).first()
    itn = db_session.query(InstitutionTypeName).first()
    out = db_session.query(OrgUnitType).first()
    client = Client(
        slug="test-org-client",
        display_name="Test Org Client",
        legal_name="Test Org Client Ltd",
        legal_entity_type_id=let.id,
        primary_contact_email="info@testorgclient.com",
    )
    db_session.add(client)
    db_session.flush()

    itype = InstitutionType(name_id=itn.id, code="SCH2", is_system=True)
    db_session.add(itype)
    db_session.flush()

    inst = Institution(
        client_id=client.id,
        institution_type_id=itype.id,
        display_name="Test Org Inst",
    )
    db_session.add(inst)
    db_session.flush()

    org = OrgUnit(
        client_id=client.id,
        institution_id=inst.id,
        name="Root Dept",
        type_id=out.id,
    )
    db_session.add(org)
    db_session.flush()
    assert isinstance(org.id, uuid.UUID)
    assert org.id.version == 4


def test_approval_pk_is_uuid_v4(db_session: Session):
    """Approval PK is a UUID v4 (AC-2)."""
    approval = Approval(requested_by="test-user")
    db_session.add(approval)
    db_session.flush()
    assert isinstance(approval.id, uuid.UUID)
    assert approval.id.version == 4


def test_no_autoincrement_sequences(db_engine):
    """No SERIAL/BIGSERIAL/IDENTITY autoincrement columns on C-01 tables (AC-2)."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name IN (
                'client', 'institution', 'institution_type', 'org_unit',
                'legal_entity_type', 'org_unit_type', 'institution_type_name',
                'approval', 'client_lifecycle_event',
                'institution_lifecycle_event', 'ownership_transfer_event'
            )
            AND (data_type LIKE '%serial%' OR data_type = 'integer' AND column_name = 'id')
        """))
        rows = result.fetchall()
        # No serial/identity columns should exist
        assert len(rows) == 0, f"Found autoincrement columns: {rows}"
