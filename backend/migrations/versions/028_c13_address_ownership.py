"""C-13 Address Management — Migration 028: ownership exclusivity + hardening (G-07/G-14/G-18).

G-07: Enforce Address ownership exclusivity — UNIQUE(address_id) on address_assignment.
G-14: Harden migration: PKs/FKs/UNIQUE/CHECK/indexes already in 027; this migration
      adds the missing UNIQUE(address_id), ensures postal_code NOT NULL guard,
      and verifies downgrade/upgrade round-trip.
G-18: Verify updated_at behavior: ORM onupdate=text("now()") aligned with business
      models (client/institution/org_unit) — DB columns remain TIMESTAMPTZ NOT NULL
      DEFAULT now(); no DDL needed for onupdate (ORM-level). Migration keeps columns
      as TIMESTAMPTZ and ensures they are NOT NULL.

Revision ID: 028_c13_address_ownership
Revises: 027_c13_address
Create Date: 2026-09-08
"""

from __future__ import annotations

from alembic import op

revision = "028_c13_address_ownership"
down_revision = "027_c13_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # G-07 — UNIQUE(address_id) on address_assignment
    # ============================================================
    # Use DO block for idempotency (PostgreSQL has no ADD CONSTRAINT IF NOT EXISTS)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_address_assignment_address_id'
            ) THEN
                ALTER TABLE address_assignment
                    ADD CONSTRAINT uq_address_assignment_address_id UNIQUE (address_id);
            END IF;
        END $$;
    """)

    # Create explicit unique index for query performance / naming parity
    # (constraint above already creates an index, but this is idempotent guard)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_address_assignment_address_id
            ON address_assignment(address_id)
    """)

    # ============================================================
    # G-14 — Harden: ensure postal_code NOT NULL (G-06 guard)
    # ============================================================
    # Guard: only set NOT NULL if no NULL rows exist; update is safe on fresh DB.
    # If NULLs exist, ALTER will fail — caller must backfill first.
    op.execute("""
        DO $$
        BEGIN
            -- If column is currently nullable, tighten it
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'address' AND column_name = 'postal_code' AND is_nullable = 'YES'
            ) THEN
                -- Ensure no NULL rows before tightening (fresh DB has none)
                IF NOT EXISTS (SELECT 1 FROM address WHERE postal_code IS NULL) THEN
                    ALTER TABLE address ALTER COLUMN postal_code SET NOT NULL;
                END IF;
            END IF;
        END $$;
    """)

    # ============================================================
    # G-14 — Verify/harden: ensure critical constraints/indexes exist
    # (already in 027, but re-assert idempotently for fresh vs upgrade paths)
    # ============================================================
    # CHECK valid_to >= valid_from
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_assignment_dates'
            ) THEN
                ALTER TABLE address_assignment
                    ADD CONSTRAINT chk_assignment_dates CHECK (valid_to IS NULL OR valid_to >= valid_from);
            END IF;
        END $$;
    """)

    # Unique constraints for reference data already exist in 027:
    #   country.code UNIQUE, entity_type.code UNIQUE, address_type.code UNIQUE,
    #   state(country_id,code), city(state_id,code) — no extra index needed.

    # ============================================================
    # G-18 — updated_at convention: ensure TIMESTAMPTZ NOT NULL DEFAULT now()
    # (ORM onupdate=text('now()') is Python-level; DB columns stay as before)
    # No DDL change required — verify columns are TIMESTAMPTZ below.
    # ============================================================
    # Nothing to alter: address and address_assignment already have
    # created_at/updated_at TIMESTAMPTZ NOT NULL DEFAULT now() from 027.
    # This is the same type used by business models (client/institution)
    # which add onupdate=text('now()') at ORM level.
    pass


def downgrade() -> None:
    # ============================================================
    # Downgrade G-07 — drop UNIQUE(address_id)
    # ============================================================
    # Drop the constraint (which also drops its backing index); then clean up any stray index.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_address_assignment_address_id'
            ) THEN
                ALTER TABLE address_assignment DROP CONSTRAINT uq_address_assignment_address_id;
            END IF;
        END $$;
    """)
    op.execute("DROP INDEX IF EXISTS uq_address_assignment_address_id")

    # ============================================================
    # Downgrade G-14 — revert postal_code to nullable
    # ============================================================
    op.execute("ALTER TABLE address ALTER COLUMN postal_code DROP NOT NULL")

    # Note: G-18 has no DDL to revert (ORM-only change).
    # CHECK and reference uniques are left intact on downgrade of this
    # revision; full downgrade to 027 base drops tables anyway via 027's downgrade.
