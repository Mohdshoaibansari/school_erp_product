## Context

C-13 Address Management was introduced in change `add-c13-address-management` (7 new tables, 54 tasks). Post-implementation review produced `C-13-Address-Management-Gap-Register-and-Implementation-Plan.md` documenting 19 gaps (G-01..G-19) across wiring, resolution, validation, integrity, lifecycle, mutation semantics, security, and documentation. The existing spec delta (`openspec/changes/add-c13-address-management/specs/address-management/spec.md`) still shows `postal_code` as NULLABLE and lacks explicit constraints for `UNIQUE(address_id)`, temporal one-effective enforcement, hierarchy invocation, and update-vs-correction separation. This change hardens the implementation to match the PRD decisions locked 2026-09-07 (D1-D15) without rebuilding the architecture.

Current state:
- Module at `backend/kernel/address/` with models (`address.py`, `address_assignment.py`, `address_type.py`, `entity_type.py`, `country.py`, `state.py`, `city.py`), repos, services, routes (`addresses.py`, `person_addresses.py`, `institution_addresses.py`, `reference_data.py`, `address_types.py`), schemas/DTOs, and migration `027_c13_address`.
- Composition: `backend/main.py` does not yet wire C-13 routes.
- EntityType/AddressType resolution: placeholder `uuid4()` in person/institution routes.
- Compatibility: `list_compatible_types()` returns all types.
- Validation: hierarchy helper exists but not invoked on all write paths; `postal_code` nullable in spec/migration; whitespace rules incomplete.
- Integrity: no `UNIQUE(address_id)` on `address_assignment`.
- Temporal: overlap check exists but one-effective and historical/future state handling not fully enforced.
- Workflows: replacement/deletion/correction exist conceptually but not fully transactional/audited with before/after.
- Security: tenant isolation derived from entity, C-04 app-level (no RLS), but unverified with real DB tests.
- Tests: `backend/tests/test_c13_address.py` is mock-heavy.
- Docs: `AGENTS.md` capability table stale; PRD §7 `postal_code No` pending `Yes` amendment.

## Goals / Non-Goals

**Goals:**
- Close all 19 gaps with minimal, verifiable changes ordered by Phase A→G (wiring → validation → integrity → lifecycle → mutation → security → verification).
- Enforce code-based EntityType/AddressType resolution, correct compatibility filtering, mandatory hierarchy validation, `postal_code NOT NULL` + whitespace normalization, `UNIQUE(address_id)`, temporal one-effective/overlap invariants, and atomic replacement/deletion/correction with audit.
- Preserve existing module boundaries, C-04 as sole authorizer, and derived-scope model (no `client_id`/`institution_id` on C-13 tables).
- Upgrade tests to real DB/API coverage and synchronize capability documentation.

**Non-Goals:**
- No geospatial expansion (lat/long, GPS, geocoding, maps, zones) — deferred per PRD §2.
- No physical `Location` entity or pickup/drop-point management.
- No RLS introduction (Phase 1 = app-level C-04; RLS additive later if required).
- No pagination/filtering or API idempotency additions.
- No C-01/C-02 historical behavioral changes.
- No schema redesign beyond constraint tightening (`postal_code NOT NULL`, `UNIQUE(address_id)`, CHECK, indexes).
- No new config keys (C-08).

## Decisions

### D1 — Module `kernel/address/` (singular) — G-01
**Decision:** Keep `backend/kernel/address/` as the sole C-13 module location; wire it in `backend/main.py` via the same composition mechanism used by `kernel/tenant_institution`, `kernel/user`, etc.
**Alternatives:** New package `kernel/addresses` (plural) — rejected: breaks convention and existing imports. Eager RLS wiring — rejected: C-04 app-level is Phase 1.

### D2 — Only 2 EntityTypes `INSTITUTION`, `PERSON` — G-02
**Decision:** Phase 1 seeds exactly `INSTITUTION` (C-01) and `PERSON` (C-02, covering Student/Employee/Staff via Person FK). Codes immutable, names immutable, registered deterministically by migration.
**Alternatives:** Separate `STUDENT`/`EMPLOYEE` EntityTypes — rejected: duplicates Person identity; future modules reference Person.

### D3 — Generic polymorphic `entity_type_id` + `entity_id` (Option A) — G-02/G-03
**Decision:** `address_assignment` uses `entity_type_id` FK + `entity_id` UUID (no FK) with application-level existence validation. Scope derived at service time.
**Alternatives:** Separate FK columns per entity type — rejected: not generic, requires schema change per consumer. JSONB polymorphic — rejected: no FK benefit, harder indexing.

### D4 — No `client_id`/`institution_id` on `address`/`address_assignment` — scope derived — G-13
**Decision:** Retain derived scope; resolve entity → scope facts → build `ResourceContext` → C-04 decision. No redundant tenant columns.
**Alternatives:** Duplicate tenant columns for easier RLS — rejected: violates PRD §13/#60-62 and `AGENTS.md §8` config-first; second source of truth.

### D5 — C-04 app-level authorization, no RLS in Phase 1 — G-13/G-16
**Decision:** C-04/Casbin remains sole decision-maker; `address.create/read/update/delete/correct`, `address_type.read/manage` flow through existing FastAPI middleware and `ProviderRegistry`. RLS deferred.
**Alternatives:** Introduce RLS on C-13 — rejected: premature complexity; polymorphic rows not amenable to simple RLS.

### D6 — Seed India geographic data (1 country, 28 states, 45 cities) minimal intentional — G-17
**Decision:** Migration seeds `IN` + ~28 states + 45 major cities; codes hierarchical unique (`Country.code`, `State(country_id,code)`, `City(state_id,code)`); seed is migration/seed-managed, no runtime CRUD.
**Alternatives:** Full India city dataset — rejected: out of Phase 1 scope, bloat. Runtime CRUD APIs — rejected: violates PRD §8 administration rule.

### D7 — App-level temporal overlap validation — G-08
**Decision:** Overlap and one-effective checks remain application-level queries before create/update; `CHECK (valid_to >= valid_from)` at DB layer. Adjacent periods allowed.
**Alternatives:** DB exclusion constraint (`EXCLUDE USING gist`) — rejected: requires `btree_gist`, complicates polymorphic scope; deferred to performance phase.

### D8 — Hard delete `AddressAssignment` + owned `Address` (no orphan, no reuse) + `UNIQUE(address_id)` — G-07/G-10
**Decision:** Add `UNIQUE(address_id)` on `address_assignment`; service pre-checks reuse but DB is the concurrency backstop. Delete is always via assignment ownership in one transaction.
**Alternatives:** Allow reuse with reference count — rejected: violates PRD §10-11 entity-owned semantics.

### D9 — Single transactional `replace_address()` (end old, create new Address, new assignment) — G-09
**Decision:** Service method `replace_address()` within one DB transaction; never mutates old Address row; validates hierarchy/compatibility/dates for new row.
**Alternatives:** Client-orchestrated multi-call replace — rejected: not atomic, risk of partial state.

### D10 — Separate `address.correct` endpoint for effective addresses — G-11/G-12
**Decision:** `POST /addresses/{id}/correct` requires `address.correct`; ordinary `PATCH` gated to future only; effective addresses rejected on ordinary path.
**Alternatives:** Reuse `PATCH` with flag — rejected: blurs authorization boundary, audit distinction lost.

### D11 — Composite unique codes: Country `code`, State `(country_id,code)`, City `(state_id,code)` — G-05/G-14
**Decision:** Keep scoped uniqueness as migrated; hierarchy validation complements it at application layer.
**Alternatives:** Global unique city codes — rejected: collisions across states.

### D12 — Audit via existing `AuditEmitter` (`address.created/corrected/deleted` etc.) — G-12
**Decision:** Integrate `kernel/audit/AuditEmitter`; `address.corrected` emits `before`/`after`; no parallel audit store.
**Alternatives:** Custom audit table for C-13 — rejected: second mechanism violates guardrail #4.

### D13 — All routes in `kernel/address/routes/` (Option 1 refined) — G-01
**Decision:** Retain `addresses.py` (generic GET/PATCH/DELETE/correct/replace), `person_addresses.py`, `institution_addresses.py`, `reference_data.py`, `address_types.py`.
**Alternatives:** Centralized `/addresses/assignments` generic only — rejected: loses entity-scoped ergonomics already designed.

### D14 — `postal_code` required `VARCHAR(20) NOT NULL` — overrides PRD §7 `No` — G-06
**Decision:** Alter `address.postal_code` to `NOT NULL`; application enforces required + blank→`ADDRESS_REQUIRED_FIELD`; amendment `No → Yes` pending docs-first commit per `AGENTS.md §3`.
**Alternatives:** Keep nullable with optional behavior — rejected: contradicted by 2026-09-07 grill lock (user-confirmed).

### D15 — `locality`/`landmark` remain optional 100, blank→NULL — G-06
**Decision:** Optional text fields normalize whitespace-only/missing/null to `NULL`; trimming is leading/trailing only.
**Alternatives:** Store empty string — rejected: violates PRD §12 empty-value rule, creates dual representation.

## Risks / Trade-offs

- **Concurrent duplicate `address_id` assignment** → Mitigation: `UNIQUE(address_id)` at DB layer; service pre-check is optimistic.
- **Compatibility filtering regression** → Mitigation: unit + integration tests for `PERSON`/`INSTITUTION` matrices and unconfigured-empty case.
- **postal_code NOT NULL migration on existing data** → Mitigation: backfill guard in migration; reject `NULL` at application before DDL; verify fresh + upgrade paths.
- **Temporal overlap race** → Mitigation: application query in transaction with `SELECT ... FOR UPDATE` or serializable retry; DB CHECK as second layer.
- **Derived-scope isolation bypass via polymorphic `entity_id`** → Mitigation: entity existence + scope resolution before every C-13 operation; cross-scope tests for same/different institution/client and Platform Owner.
- **Audit transactional coupling** → Mitigation: `AuditEmitter` called within same transaction where platform requires atomicity; rollback verified.
- **Reference-data drift (India seed)** → Mitigation: idempotent seed by `code`; codes immutable; no runtime CRUD.
- **updated_at divergence** → Mitigation: align with existing kernel convention (`server_default=now()`, `onupdate=now()`), verified by persistence test.

## Migration Plan

1. Alembic revision on top of `027_c13_address`:
   - `ALTER TABLE address ALTER COLUMN postal_code SET NOT NULL` (after ensuring no NULL rows; add backfill or guard).
   - `ALTER TABLE address_assignment ADD CONSTRAINT uq_address_assignment_address_id UNIQUE (address_id)`.
   - Verify `CHECK (valid_to IS NULL OR valid_to >= valid_from)` exists; add if missing.
   - Verify `UNIQUE(country_id,code)` on `state`, `UNIQUE(state_id,code)` on `city`, `UNIQUE(code)` on `country`/`entity_type`/`address_type`.
   - Seed corrections: idempotent `INSERT ... ON CONFLICT (code) DO NOTHING` for EntityType/AddressType/compatibility/geo data.
2. Permission seed idempotency check for `address.*` and `address_type.*`.
3. Rollback: downgrade drops `uq_address_assignment_address_id`, reverts `postal_code` to nullable, leaves C-13 tables (same as 027 rollback — drop tables on full downgrade).
4. Deploy: `alembic upgrade head` on fresh and existing DB; verify `alembic downgrade -1` + `upgrade head` round-trip.
5. Post-deploy: run `openspec validate fix-c13-address-gaps --type change --strict`; run full regression and `test_c13_address` DB/API suite.

## Open Questions

None — all grill decisions D1-D15 locked 2026-09-07; PRD §7 `postal_code No → Yes` amendment is a pending docs-first edit, not an open technical question for this change.
