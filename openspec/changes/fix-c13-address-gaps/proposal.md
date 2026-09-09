## Why

C-13 Address Management shipped as change `add-c13-address-management` (54 tasks) but the gap register (`C-13-Address-Management-Gap-Register-and-Implementation-Plan.md`) proves 19 gaps remain: unregistered module (G-01), random-UUID EntityType/AddressType resolution (G-02/G-03), compatibility filtering bug returning all types (G-04), missing geographic-hierarchy enforcement (G-05), incomplete `postal_code` required + whitespace normalization (G-06), missing `UNIQUE(address_id)` allowing reuse (G-07), incomplete temporal/one-effective enforcement (G-08), non-atomic replacement (G-09), non-atomic deletion leaving orphans (G-10), ordinary update bypassing correction (G-11), and incomplete correction audit (G-12), plus migration/RLS/test/doc gaps (G-13..G-19). Without this fix the C-13 spec is not enforceable and address data integrity, temporal correctness, and tenant isolation are unverified.

## What Changes

- **G-01** — Register `kernel/address` in application composition via existing manifest/composition mechanism; routes become reachable and OpenAPI-visible.
- **G-02** — Resolve `EntityType` by immutable `code` (`PERSON`, `INSTITUTION`) via centralized `EntityTypeRepo/Service`; remove `uuid4()` placeholder in `person_addresses.py` and all routes.
- **G-03** — Resolve `AddressType` by immutable `code` (`RESIDENTIAL`, `PERMANENT`, `CORRESPONDENCE`, `OFFICE`, `EMERGENCY`) via centralized `AddressTypeRepo/Service`; remove random-UUID placeholder; validate compatibility.
- **G-04** — Fix `AddressTypeService.list_compatible_types()` to return only compatible AddressTypes (unconfigured = denied) resolved via registered `EntityType`.
- **G-05** — Enforce geographic hierarchy (`city.state_id == state.id` AND `state.country_id == country.id`) on every write path (`create`, `update`, `correct`, `replace`); reject mismatched or missing references; keep Country/State/City seed/migration-managed.
- **G-06** — Enforce `postal_code` **required** `VARCHAR(20) NOT NULL` (2026-09-07 grill amendment, overrides PRD §7 `No`); trim leading/trailing whitespace on all text fields; optional whitespace-only → `NULL`; required whitespace-only → `ADDRESS_REQUIRED_FIELD`; never silently truncate; max-length checks for `address_line_1`/`address_line_2` (500), `locality`/`landmark` (100), `postal_code` (20).
- **G-07** — Enforce Address ownership exclusivity: `address_assignment.address_id` SHALL have `UNIQUE` constraint; service SHALL reject duplicate ownership; concurrent duplicates fail safely via DB constraint.
- **G-08** — Complete temporal lifecycle: `valid_from` mandatory, `valid_to` inclusive, reject `valid_to < valid_from`, reject overlapping periods for same `entity + AddressType`, enforce at most one effective assignment (`valid_from <= today <= valid_to` or `valid_to IS NULL`), support future/historical/same-day/adjacent periods; historical assignments remain queryable.
- **G-09** — Implement atomic replacement/move: end old assignment (`valid_to`), create new `Address`, create new `AddressAssignment` in one transaction; old Address remains historical; rollback on failure; never reuse Address rows.
- **G-10** — Implement atomic deletion: delete via `AddressAssignment` ownership; delete `AddressAssignment` + owned `Address` in one transaction; no orphan; no independent Address delete bypassing assignment.
- **G-11** — Enforce ordinary `update` vs correction separation: ordinary `PATCH` SHALL only mutate future addresses; effective-address mutation SHALL be rejected and require `POST .../correct`; historical addresses SHALL be immutable via ordinary update.
- **G-12** — Complete effective-address correction semantics + audit: require `address.correct` permission; allow only when address is effective; capture before/after; apply transactionally via `AuditEmitter`; emit `address.corrected` with diff; rollback on audit/write failure.
- **G-13** — Verify tenant/RLS compatibility: scope derived from target entity (no `client_id`/`institution_id` on C-13 tables); C-04 app-level authorization remains primary; polymorphic association cannot bypass isolation.
- **G-14** — Verify/harden migration and DB constraints (PKs, FKs, UNIQUE, CHECK `valid_to >= valid_from`, indexes, `NOT NULL`, timestamps).
- **G-15** — Replace weak mock-only tests with real DB/API coverage for validation, hierarchy, compatibility, temporal, replacement, deletion, correction, authorization, isolation, rollback.
- **G-16** — Verify C-04 authorization integration: C-13 MUST NOT implement own engine; `address.create/read/update/delete/correct` and `address_type.*` flow through existing middleware/Casbin with correct `ResourceContext`.
- **G-17** — Verify geographic reference data scope: India seed (1 country, 28 states, 45 cities) is intentional minimal; codes stable/immutable; no runtime CRUD.
- **G-18** — Verify `updated_at` behavior aligns with project conventions (DB default + ORM `onupdate`).
- **G-19** — Synchronize documentation and capability status in `AGENTS.md`; no architectural decisions changed without ADR.

## Capabilities

### New Capabilities

None — this is a gap-fix delta on an existing capability.

### Modified Capabilities

- `address-management`: Corrects and hardens the C-13 Address Management capability to close G-01..G-19 — EntityType/AddressType resolution by code, compatibility filtering, hierarchy enforcement, `postal_code` required + whitespace rules, `UNIQUE(address_id)`, temporal one-effective/overlap rules, atomic replacement, atomic deletion, update-vs-correction separation, and correction audit. Each behavior change is captured as a MODIFIED Requirement delta.

## Impact

- **Code:** `backend/kernel/address/` (models, repos, services, routes, schemas), `backend/main.py` (registration), `backend/alembic/migrations/027_c13_address*` (constraints, `postal_code NOT NULL`, `UNIQUE(address_id)`), `backend/tests/test_c13_address.py` (expanded).
- **APIs:** No new endpoints; hardening of `GET/POST /persons/{id}/addresses`, `GET/POST /institutions/{id}/addresses`, `GET/PATCH/DELETE /addresses/{id}`, `POST /addresses/{id}/correct`, `POST /addresses/{id}/replace`, `GET /address-types*`, `GET /countries|states|cities`.
- **Dependencies:** C-01 Institution, C-02 Person (scope derivation), C-04 Authorization (sole decision-maker; 8 permissions), C-11 Audit (`AuditEmitter`), C-08 Configuration Framework (no new keys), PostgreSQL (CHECK/UNIQUE/FK constraints).
- **Migration:** Idempotent seed updates (EntityType/AddressType by `code`), `postal_code` `NULL → NOT NULL` backfill guard, `UNIQUE(address_id)` index; downgrade drops C-13 tables.
- **Docs:** Pending PRD §7 `postal_code No → Yes` amendment (docs-first per `AGENTS.md §3`); `AGENTS.md` capability table status sync; no new repo-level ADR (review in `adr.md`).
