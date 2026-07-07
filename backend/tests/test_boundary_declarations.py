"""Boundary declaration tests (tasks 14.1–14.4, AC-18, AC-17).

14.1 — C-01 has NO foreign key to C-05 (D10 zero-dependency invariant).
14.2 — `homeroom_teacher_id` is NOT a field on OrgUnit (belongs to C-05/C-02).
14.3 — tz/locale/currency/branding/`academic_year_start`/`grading_scale` are
       NOT intrinsic on Client or Institution (delegated to C-08).
14.4 — no MODIFIED/REMOVED deltas exist for any other domain — every
       requirement is ADDED under `tenant-institution` (AC-18).
"""

from __future__ import annotations

import pathlib

from sqlalchemy import text


# ============================================================
# 14.1 — C-01 has NO FK to C-05 (D10, AC-18)
# ============================================================

# All C-01-owned tables (the set the D10 invariant applies to)
_C01_TABLES = (
    "client", "institution", "institution_type", "org_unit",
    "approval", "client_lifecycle_event",
    "institution_lifecycle_event", "ownership_transfer_event",
    "legal_entity_type", "org_unit_type", "institution_type_name",
)

# C-05 (Academic Structure) entities — these MUST NOT be referenced by a C-01 FK
_C05_TABLES = (
    "academic_year", "term", "subject", "class_subject",
    "homeroom_assignment", "academic_assignment",
    "academic_year_institution", "grade_level", "section",
)


def test_no_c01_fk_references_c05(db_engine):
    """14.1, D10, AC-18: no C-01 table has a FK to a C-05 entity."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS referenced_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.constraint_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.constraint_schema = ccu.constraint_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
        """))
        violations = []
        for row in result:
            table_name, _col, ref_table = row[0], row[1], row[2]
            if table_name in _C01_TABLES and ref_table in _C05_TABLES:
                violations.append(f"{table_name} -> {ref_table}")
        assert violations == [], (
            f"C-01 tables reference C-05 entities (D10 invariant violated): {violations}"
        )


# ============================================================
# 14.2 — homeroom_teacher_id NOT on OrgUnit (AC-18)
# ============================================================

def test_org_unit_has_no_homeroom_teacher_id(db_engine):
    """14.2, AC-18: OrgUnit has no homeroom_teacher_id column (belongs to C-05/C-02)."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'org_unit'
                AND column_name = 'homeroom_teacher_id'
        """))
        assert result.fetchall() == [], (
            "homeroom_teacher_id must NOT be a field on OrgUnit (D10, AC-18) — "
            "it belongs to C-05 (academic assignment) or C-02 RoleAssignment"
        )


# ============================================================
# 14.3 — tz/locale/currency/branding/academic_year_start/grading_scale
#         NOT intrinsic on Client or Institution (AC-17, C-08 delegation)
# ============================================================

# Full D11/D4/D5 forbidden list for 14.3
_C08_DELEGATED_COLUMNS = {
    "timezone", "locale", "currency",
    "logo_url", "brand_color", "theme", "branding",
    "academic_year_start", "grading_scale",
}


def test_client_has_no_c08_delegated_columns(db_engine):
    """14.3, AC-17: Client has none of the C-08-delegated columns."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'client'
        """))
        cols = {row[0] for row in result}
        forbidden = _C08_DELEGATED_COLUMNS & cols
        assert not forbidden, (
            f"Client has C-08-delegated columns (must be delegated, AC-17): {forbidden}"
        )


def test_institution_has_no_c08_delegated_columns(db_engine):
    """14.3, AC-17: Institution has none of the C-08-delegated columns."""
    with db_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'institution'
        """))
        cols = {row[0] for row in result}
        forbidden = _C08_DELEGATED_COLUMNS & cols
        assert not forbidden, (
            f"Institution has C-08-delegated columns (must be delegated, AC-17): {forbidden}"
        )


# ============================================================
# 14.4 — no MODIFIED/REMOVED deltas for any other domain (AC-18)
# ============================================================

_SPEC_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "openspec" / "changes" / "add-c01-tenant-institution" / "specs"
)


def test_only_tenant_institution_spec_domain_exists():
    """14.4, AC-18: the change has only the `tenant-institution` domain spec (no other domain)."""
    domains = sorted(
        p.name for p in _SPEC_PATH.iterdir() if p.is_dir()
    )
    assert domains == ["tenant-institution"], (
        f"Only the tenant-institution domain spec is expected (AC-18): found {domains}"
    )


def test_only_added_requirements_in_spec():
    """14.4, AC-18: the spec has only ADDED requirements (no MODIFIED/REMOVED deltas)."""
    spec_file = _SPEC_PATH / "tenant-institution" / "spec.md"
    content = spec_file.read_text(encoding="utf-8")
    # OpenSpec delta headers
    assert "## ADDED Requirements" in content, "spec.md must have an ADDED Requirements header"
    # No MODIFIED or REMOVED delta sections for any domain
    for forbidden in ("## MODIFIED Requirements", "## REMOVED Requirements"):
        assert forbidden not in content, (
            f"spec.md must not contain a '{forbidden}' section (AC-18 — "
            "every requirement is ADDED under tenant-institution)"
        )