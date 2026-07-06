"""Tests for Client/Institution field purity (AC-17).

Verifies: no tz/locale/currency/branding/subscription/billing columns on Client
or Institution tables; no academic structure columns.
"""

from __future__ import annotations

from sqlalchemy import text

# Columns that MUST NOT exist on Client or Institution (D4, D5, AC-17)
FORBIDDEN_CLIENT_COLUMNS = {
    "timezone", "locale", "currency", "logo_url", "brand_color", "theme",
    "subscription_state", "billing_plan", "payment_method", "contract_id",
    "academic_year_start", "grading_scale",
}

FORBIDDEN_INSTITUTION_COLUMNS = {
    "timezone", "locale", "currency", "logo_url", "brand_color", "theme",
    "academic_year_start", "grading_scale",
    # C-05 academic structure (D10, AC-18)
    "homeroom_teacher_id", "academic_year_id", "term_id", "subject_id",
}

# Columns that MUST exist on Client (D4)
REQUIRED_CLIENT_COLUMNS = {
    "id", "slug", "display_name", "legal_name", "legal_entity_type_id",
    "tax_registration_number", "primary_contact_email",
    "primary_contact_phone", "billing_contact_email", "address_id",
    "current_lifecycle_status", "created_at", "updated_at", "archived_at",
}

# Columns that MUST exist on Institution (D5)
REQUIRED_INSTITUTION_COLUMNS = {
    "id", "client_id", "institution_type_id", "display_name", "legal_name",
    "code", "primary_contact_email", "primary_contact_phone", "address_id",
    "current_lifecycle_status", "established_year", "affiliation_number",
    "affiliation_board", "created_at", "updated_at", "archived_at",
}

# Columns that MUST exist on OrgUnit (D6) — and NOT homeroom_teacher_id (D10, AC-18)
REQUIRED_ORG_UNIT_COLUMNS = {
    "id", "client_id", "institution_id", "parent_id", "name", "type_id",
    "sort_order", "code", "current_lifecycle_status",
    "created_at", "updated_at", "archived_at",
}

FORBIDDEN_ORG_UNIT_COLUMNS = {
    "homeroom_teacher_id", "academic_year_id", "term_id", "subject_id",
    "grade_level", "section_type",
}


def _get_columns(db_engine, table_name: str) -> set[str]:
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table
        """), {"table": table_name})
        return {row[0] for row in result}


def test_client_has_no_client_id_column(db_engine):
    """Client table has NO client_id column (Q1 — Client IS the tenant)."""
    cols = _get_columns(db_engine, "client")
    assert "client_id" not in cols


def test_client_field_purity(db_engine):
    """Client carries only identity/lifecycle fields (AC-17)."""
    cols = _get_columns(db_engine, "client")
    forbidden = FORBIDDEN_CLIENT_COLUMNS & cols
    assert not forbidden, f"Client has forbidden columns: {forbidden}"
    missing = REQUIRED_CLIENT_COLUMNS - cols
    assert not missing, f"Client missing required columns: {missing}"


def test_institution_field_purity(db_engine):
    """Institution carries only identity/lifecycle fields (AC-17)."""
    cols = _get_columns(db_engine, "institution")
    forbidden = FORBIDDEN_INSTITUTION_COLUMNS & cols
    assert not forbidden, f"Institution has forbidden columns: {forbidden}"
    missing = REQUIRED_INSTITUTION_COLUMNS - cols
    assert not missing, f"Institution missing required columns: {missing}"


def test_org_unit_purity(db_engine):
    """OrgUnit is pure structure — no academic metadata (D10, AC-18)."""
    cols = _get_columns(db_engine, "org_unit")
    forbidden = FORBIDDEN_ORG_UNIT_COLUMNS & cols
    assert not forbidden, f"OrgUnit has forbidden columns: {forbidden}"
    missing = REQUIRED_ORG_UNIT_COLUMNS - cols
    assert not missing, f"OrgUnit missing required columns: {missing}"


def test_client_has_no_fk_to_c05(db_engine):
    """C-01 has no FK to C-05 entities (D10, AC-18)."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS referenced_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name IN (
                    'client', 'institution', 'institution_type', 'org_unit',
                    'approval', 'client_lifecycle_event',
                    'institution_lifecycle_event', 'ownership_transfer_event'
                )
        """))
        c05_tables = {"academic_year", "term", "subject", "class_subject",
                      "homeroom_assignment", "academic_assignment"}
        for table_name, col_name, ref_table in result:
            assert ref_table not in c05_tables, \
                f"FK from {table_name}.{col_name} references C-05 table {ref_table}"
