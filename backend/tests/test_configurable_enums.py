"""Tests for configurable enums backed by lookup tables (AC-20, Q2).

Verifies: adding a new enum value is a data insert, no code change.
"""

from __future__ import annotations

from sqlalchemy import text

from kernel.tenant_institution.models import (
    LegalEntityType,
    OrgUnitType,
    InstitutionTypeName,
)


def test_legal_entity_types_seeded(db_session):
    """Seed data for legal entity types exists (task 3.4)."""
    types = db_session.query(LegalEntityType).all()
    names = {t.name for t in types}
    assert "Sole Proprietor" in names
    assert "Partnership" in names
    assert "Pvt Ltd" in names
    assert "Trust" in names
    assert "Society" in names


def test_org_unit_types_seeded(db_session):
    """Seed data for OrgUnit types exists (task 3.4)."""
    types = db_session.query(OrgUnitType).all()
    names = {t.name for t in types}
    expected = {"Department", "Faculty", "Grade", "Division", "Section",
                "Class", "Program", "Batch", "Course"}
    assert expected.issubset(names)


def test_institution_type_names_seeded(db_session):
    """Seed data for InstitutionType names exists (task 3.4)."""
    names = db_session.query(InstitutionTypeName).all()
    name_set = {n.name for n in names}
    assert "School" in name_set
    assert "College" in name_set
    assert "University" in name_set
    assert "Coaching Institute" in name_set


def test_add_legal_entity_type_via_data_insert(db_session):
    """Adding a new legal entity type is a data insert, no code change (AC-20)."""
    new_type = LegalEntityType(name="Limited Liability Partnership")
    db_session.add(new_type)
    db_session.flush()
    assert new_type.id is not None
    # Verify it's queryable
    found = db_session.query(LegalEntityType).filter_by(name="Limited Liability Partnership").first()
    assert found is not None


def test_add_org_unit_type_via_data_insert(db_session):
    """Adding a new OrgUnit type is a data insert (AC-20)."""
    new_type = OrgUnitType(name="Campus")
    db_session.add(new_type)
    db_session.flush()
    assert new_type.id is not None
    found = db_session.query(OrgUnitType).filter_by(name="Campus").first()
    assert found is not None


def test_add_institution_type_name_via_data_insert(db_session):
    """Adding a new InstitutionType name is a data insert (AC-20)."""
    new_name = InstitutionTypeName(name="Polytechnic")
    db_session.add(new_name)
    db_session.flush()
    assert new_name.id is not None
    found = db_session.query(InstitutionTypeName).filter_by(name="Polytechnic").first()
    assert found is not None


def test_entity_tables_fk_reference_lookups(db_engine):
    """Entity tables FK-reference lookup tables, not hardcoded check constraints (AC-20)."""
    with db_engine.connect() as conn:
        # Client.legal_entity_type_id → legal_entity_type.id
        result = conn.execute(text("""
            SELECT tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'client' AND kcu.column_name = 'legal_entity_type_id'
                AND tc.constraint_type = 'FOREIGN KEY'
        """))
        assert result.fetchone() is not None, "Client.legal_entity_type_id is not an FK"

        # OrgUnit.type_id → org_unit_type.id
        result = conn.execute(text("""
            SELECT tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'org_unit' AND kcu.column_name = 'type_id'
                AND tc.constraint_type = 'FOREIGN KEY'
        """))
        assert result.fetchone() is not None, "OrgUnit.type_id is not an FK"

        # InstitutionType.name_id → institution_type_name.id
        result = conn.execute(text("""
            SELECT tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'institution_type' AND kcu.column_name = 'name_id'
                AND tc.constraint_type = 'FOREIGN KEY'
        """))
        assert result.fetchone() is not None, "InstitutionType.name_id is not an FK"
