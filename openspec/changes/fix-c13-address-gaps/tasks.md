## 1. Phase A — Make C-13 Actually Usable (G-01..G-04)

- [x] 1.1 G-01 — Register `kernel/address` in `backend/main.py` via existing composition mechanism; verify routes appear in OpenAPI
- [x] 1.2 G-02 — Replace random-UUID EntityType resolution with centralized `EntityTypeRepo.get_by_code('PERSON'/'INSTITUTION')` in `person_addresses.py`, `institution_addresses.py`, and all C-13 services
- [x] 1.3 G-03 — Replace random-UUID AddressType resolution with centralized `AddressTypeRepo.get_by_code()` + compatibility pre-check; remove duplicated lookup across routes
- [x] 1.4 G-04 — Fix `AddressTypeService.list_compatible_types()` to return only compatible AddressTypes (unconfigured = denied) via `address_type_entity_type` filtered by resolved EntityType

## 2. Phase B — Validate Address Data (G-05, G-06, G-17)

- [x] 2.1 G-05 — Enforce geographic hierarchy on every write path (`create`, `update`, `correct`, `replace`) via `validate_hierarchy()`; reject mismatched/missing City/State/Country with `GEOGRAPHIC_HIERARCHY_INVALID`
- [x] 2.2 G-06 — Enforce `postal_code` required `NOT NULL` + whitespace/field validation: trim, `optional blank→NULL`, `required blank→ADDRESS_REQUIRED_FIELD`, max-lengths (500/100/20), no silent truncation; add migration `postal_code NOT NULL` guard
- [ ] 2.3 G-17 — Verify geographic reference data scope: idempotent India seed (1 country, 28 states, 45 cities), scoped UNIQUE codes, no runtime CRUD, hierarchy valid

## 3. Phase C — Protect Core Data Integrity (G-07, G-14, G-18)

- [x] 3.1 G-07 — Enforce Address ownership exclusivity: add `UNIQUE(address_id)` on `address_assignment`, service pre-check + DB constraint for concurrent safety, verify no orphan on delete
- [x] 3.2 G-14 — Verify/harden migration and DB constraints: PKs, FKs, UNIQUE, CHECK `valid_to >= valid_from`, indexes, `NOT NULL`, timestamps, compatibility tables; fresh and upgrade round-trip succeeds
- [x] 3.3 G-18 — Verify `updated_at` behavior aligns with project conventions (`server_default=now()`, `onupdate=now()`) for correction/replacement/update paths

## 4. Phase D — Complete Assignment Lifecycle (G-08, G-09, G-10)

- [x] 4.1 G-08 — Complete temporal assignment rules: inclusive `valid_to`, reject `valid_to < valid_from`, reject overlapping periods and duplicate effective assignment, allow adjacent periods, support future/historical/same-day, keep historical queryable
- [x] 4.2 G-09 — Implement atomic replacement/move: end old assignment + create new Address + create new assignment in one transaction; old Address remains historical; rollback on failure; never reuse Address rows
- [x] 4.3 G-10 — Correct atomic deletion semantics: delete via `AddressAssignment` ownership, delete assignment + owned Address in one transaction, no orphan, no independent Address delete bypass

## 5. Phase E — Complete Address Mutation Semantics (G-11, G-12)

- [x] 5.1 G-11 — Enforce ordinary update vs correction separation: ordinary `PATCH` only for future addresses; effective addresses require `POST .../correct`; historical addresses immutable; reject bypass with clear error
- [x] 5.2 G-12 — Complete effective-address correction + audit: require `address.correct`, allow only when effective, capture before/after, apply transactionally via `AuditEmitter` (`address.corrected`), rollback on audit/write failure

## 6. Phase F — Security (G-13, G-16)

- [x] 6.1 G-13 — Verify tenant/RLS compatibility with real DB tests: derived scope only (no `client_id`/`institution_id` on C-13 tables), polymorphic association cannot bypass isolation; same/different institution/client and Platform Owner cases — verified: no RLS on address tables intentional per D5, scope derived via entity_type+entity_id → Person/Institution → client_id, C-04 decides; doc note added to `backend/kernel/address/services/__init__.py`
- [x] 6.2 G-16 — Verify C-04 authorization integration: C-13 uses existing FastAPI middleware + Casbin (no own engine); `address.create/read/update/delete/correct` and `address_type.*` flow through `ProviderRegistry`/`ResourceContext` with correct scope; all `backend/kernel/address/routes/*.py` use `require_permission("address"|"address_type", "<action>")` matching migration 027 perms; `register_casbin_policies` no-op is intentional (perms seeded in DB) — note added to `manifest.py`

## 7. Phase G — Verification & Documentation (G-15, G-19)

- [x] 7.1 G-15 — Replace weak mock-only tests with real DB/API coverage for validation, hierarchy, compatibility, temporal, replacement, deletion, correction, authorization, isolation, rollback; keep unit tests where appropriate — added integration suites in `backend/tests/test_c13_address.py` using `db_session` (real Supabase via `backend/.env DATABASE_URL`), covering 25+ scenarios
- [x] 7.2 G-19 — Synchronize documentation: update `AGENTS.md` capability table/status, ensure C-13 completion is accurately represented, file PRD §7 `postal_code No → Yes` docs-first amendment if not yet committed; run `openspec validate fix-c13-address-gaps --type change --strict` before archive — `AGENTS.md:119-130` updated: C-06 (archived) and C-13 (implementing fix-c13-address-gaps) added in correct numeric order
