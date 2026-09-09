# C-13 Address Management — Gap Register & Implementation Plan

## Purpose

This document is the working checklist for completing the C-13 Address Management module.

It intentionally breaks the work into **small, independently implementable steps**.  
Do not attempt to fix all gaps in one change.

Use this document together with:

- `docs/prd/C-13-Address-Management-PRD.md`
- the applicable C-13 ADR/OpenSpec documents
- `docs/architecture/architecture-v1.md`
- `AGENTS.md`
- existing C-04 authorization architecture
- existing tenant/RLS conventions

## Implementation Rule

Implement **one step at a time**.

For each step:

1. Inspect the current implementation and relevant project conventions.
2. Confirm the gap still exists.
3. Make the smallest correct change.
4. Do not refactor unrelated code.
5. Add/update tests for the changed behavior.
6. Run focused tests.
7. Run relevant regression/import checks.
8. Review the diff for unnecessary changes.
9. Mark the step complete only after verification.

Do not start the next step until the current step is verified.

---

# Gap Summary

| ID | Gap | Priority | Main Area |
|---|---|---:|---|
| G-01 | C-13 is not registered in application composition | Critical | Application wiring |
| G-02 | Person route uses random EntityType UUID | Critical | EntityType resolution |
| G-03 | Person/Institution routes use random AddressType UUID | Critical | AddressType resolution |
| G-04 | AddressType compatibility filtering is incorrect | High | AddressType service |
| G-05 | Geographic hierarchy is not enforced during address create/update | High | Address validation |
| G-06 | Address field/whitespace validation needs complete enforcement | High | Validation |
| G-07 | Address can potentially be reused by multiple assignments | Critical | Database integrity |
| G-08 | AddressAssignment lifecycle/temporal rules are incomplete | Critical | Assignment lifecycle |
| G-09 | Address replacement/move semantics are incomplete | Critical | Transactional workflow |
| G-10 | Address deletion does not follow assignment + owned-address semantics | Critical | Deletion |
| G-11 | Ordinary address update does not enforce future-only rule | High | Update/correction |
| G-12 | Effective-address correction needs complete semantics and audit | High | Correction/audit |
| G-13 | C-13 tenant/RLS compatibility needs verification | Critical | Security |
| G-14 | C-13 database constraints/migration need verification | High | Migration |
| G-15 | C-13 tests are too weak and mostly mock-based | High | Testing |
| G-16 | C-13 permission integration needs verification against C-04 | Medium | Authorization |
| G-17 | Geographic seed/data scope needs verification | Medium | Reference data |
| G-18 | `updated_at` behavior needs verification | Medium | Persistence |
| G-19 | Documentation/capability status is stale | Medium | Documentation |

---

# Detailed Gaps and Steps

## Step 1 — Register C-13 in Application Composition

### Gap

C-13 has its module/manifest structure, but it is not currently registered in the main application composition.

Without registration, the module may exist in the repository but its routes are not exposed by the running FastAPI application.

### Required Work

1. Inspect the existing module registration pattern in `backend/main.py`.
2. Inspect the C-13 module manifest.
3. Register C-13 using the same composition mechanism used by existing modules.
4. Do not introduce a new registration mechanism.
5. Confirm C-13 routes are available from the running application.
6. Add an integration test for route registration if the project convention supports it.

### Verification

- Application starts successfully.
- C-13 routes appear in the FastAPI route table/OpenAPI.
- Existing application routes remain unchanged.

---

## Step 2 — Replace Random EntityType Resolution

### Gap

`backend/kernel/address/routes/person_addresses.py` contains placeholder logic that returns a random UUID for EntityType resolution.

This cannot work reliably because EntityType IDs must come from the registered EntityType data.

### Required Work

1. Inspect the EntityType model/repository/service.
2. Identify the immutable EntityType code used for Person.
3. Resolve the EntityType by its stable code.
4. Reuse the project's existing EntityType access pattern.
5. Apply the same principle anywhere C-13 resolves EntityType values.
6. Remove random UUID generation.

### Verification

- Person address operations resolve the same EntityType every time.
- Invalid/unregistered EntityType conditions fail predictably.
- No UUID generation remains in EntityType resolution.

---

## Step 3 — Replace Random AddressType Resolution

### Gap

Person and Institution address routes currently contain placeholder AddressType resolution using random UUIDs.

### Required Work

1. Inspect AddressType model/repository/service.
2. Identify the immutable AddressType codes used by the routes.
3. Resolve AddressType by code.
4. Validate that the requested AddressType is compatible with the target EntityType.
5. Remove random UUID generation.
6. Keep AddressType resolution centralized rather than duplicating lookup logic across routes.

### Verification

- Routes use real registered AddressType IDs.
- Unsupported AddressType/entity combinations are rejected.
- No random UUID is used for AddressType lookup.

---

## Step 4 — Fix AddressType Compatibility Filtering

### Gap

`AddressTypeService.list_compatible_types()` obtains compatible IDs but currently returns all AddressTypes instead of only the compatible ones.

### Required Work

1. Inspect the compatibility repository/query.
2. Correct the service so only compatible AddressTypes are returned.
3. Preserve the rule that unconfigured compatibility is denied.
4. Ensure compatibility is based on the registered EntityType.
5. Add tests for:
   - compatible type returned;
   - incompatible type excluded;
   - no compatibility configuration returns no compatible types.

### Verification

The API/service result contains only AddressTypes allowed for the target EntityType.

---

## Step 5 — Enforce Geographic Hierarchy

### Gap

The repository has hierarchy validation (`city -> state -> country`), but AddressService create/update does not consistently invoke it.

This can allow an invalid city/state/country combination.

### Required Work

1. Inspect `validate_hierarchy()`.
2. Identify where address creation and update validate geography.
3. Ensure every relevant write path invokes hierarchy validation.
4. Reject:
   - city belonging to another state;
   - state belonging to another country;
   - invalid/missing geographic references.
5. Keep Country/State/City reference data immutable as required by the PRD.

### Verification

Test valid and invalid geographic combinations through the service/API layer.

---

## Step 6 — Complete Address Field and Whitespace Validation

### Gap

C-13 requires precise validation rules for required/optional fields.

### Decision Locked 2026-09-07

`postal_code` = **required, VARCHAR(20) NOT NULL** — overrides PRD `§7` “No”. `locality`/`landmark` remain optional 100, blank→NULL. Confirmed by user 2026-09-07. PRD `§7` to be amended `No → Yes` docs-first per `AGENTS.md §3`.

### Required Work

Enforce:

- `line1`: required, max 500
- `line2`: optional, max 500
- `locality`: optional, max 100
- `landmark`: optional, max 100
- `postal_code`: **required**, max 20 (NOT NULL, blank/whitespace → `ADDRESS_REQUIRED_FIELD`, never `NULL`)
- city/state/country: required

Whitespace behavior:

- trim leading/trailing whitespace;
- optional whitespace-only values become `NULL`;
- required whitespace-only values are rejected;
- never silently truncate values.

### Verification

Add focused tests for every field boundary and whitespace case.

---

## Step 7 — Enforce Address Ownership / No Reuse

### Gap

The PRD states that an Address belongs to exactly one entity and must not be reused.

The current database model does not clearly enforce uniqueness of `address_id` across assignments.

### Required Work

1. Inspect `AddressAssignment`.
2. Add the smallest appropriate database constraint to prevent reuse.
3. Ensure the service also rejects duplicate ownership before attempting the write where useful.
4. Handle concurrent writes correctly through the database constraint/transaction.
5. Confirm deletion does not leave an assignment referencing a deleted address.

### Verification

- Same Address cannot be assigned to two entities.
- Concurrent duplicate assignment fails safely.
- Existing valid assignments continue to work.

---

## Step 8 — Complete AddressAssignment Temporal Rules

### Gap

The implementation contains overlap checking, but the complete lifecycle required by the PRD is not yet fully exposed/enforced.

Required concepts:

- historical assignments;
- current/effective assignments;
- future assignments;
- inclusive `valid_to`;
- no overlapping assignments for the same entity + AddressType;
- one effective assignment per entity + AddressType.

### Required Work

1. Define/confirm the project's exact effective-date interpretation from the PRD.
2. Implement validation for `valid_from` and `valid_to`.
3. Reject invalid date ranges.
4. Reject overlapping periods.
5. Enforce the one-effective-assignment rule.
6. Ensure historical assignments remain queryable.
7. Ensure future assignments can be created when valid.
8. Add database constraints where feasible and application validation where necessary.

### Verification

Test:

- historical;
- current;
- future;
- adjacent periods;
- overlapping periods;
- same-day boundaries;
- duplicate effective assignments.

---

## Step 9 — Implement Atomic Address Replacement / Move

### Gap

The PRD requires moving an address to be treated as a replacement operation:

1. end the old assignment;
2. create a new Address;
3. create the new AddressAssignment;
4. perform all operations atomically.

The old Address must remain historical and must never be reused.

### Required Work

1. Identify the appropriate service/API operation.
2. Implement the replacement as one transaction.
3. Close the old assignment using the correct effective date.
4. Create a completely new Address row.
5. Create a new assignment.
6. Ensure the old Address remains intact for historical records.
7. Roll back the entire operation if any step fails.

### Verification

Test both successful replacement and failure/rollback scenarios.

---

## Step 10 — Correct Address Deletion Semantics

### Gap

The current delete path directly deletes an Address.

The PRD requires deletion to operate on the ownership relationship and its owned Address:

- delete assignment;
- delete the owned Address;
- perform atomically;
- never leave an orphan Address;
- do not expose an independent business-level Address delete that violates ownership rules.

### Required Work

1. Review the current delete endpoint/service/repository.
2. Change deletion to operate using the AddressAssignment ownership.
3. Delete assignment and Address in one transaction.
4. Ensure the Address cannot be independently deleted while still assigned.
5. Handle missing/already-deleted resources consistently.

### Verification

- Successful deletion removes both rows.
- Failure rolls back.
- No orphan Address remains.
- Existing historical/business rules are preserved.

---

## Step 11 — Separate Ordinary Update from Effective Correction

### Gap

Ordinary `update_address()` currently allows updates without fully enforcing the PRD distinction between future address editing and effective-address correction.

### Required Work

1. Determine whether an Address is:
   - future;
   - effective/current;
   - historical.
2. Ordinary update should only allow the states permitted by the PRD.
3. Effective address changes must use the correction workflow.
4. Historical address behavior must follow the PRD.
5. Reject attempts to bypass correction using the ordinary update endpoint.

### Verification

Test update behavior for future, effective, and historical addresses.

---

## Step 12 — Complete Effective Address Correction and Audit

### Gap

The correction workflow exists conceptually but needs verification/completion of authorization, effective-state checks, transaction handling, and audit.

### Required Work

1. Require the dedicated `address.correct` permission.
2. Confirm the address is currently effective before allowing correction.
3. Capture before-state.
4. Apply the correction transactionally.
5. Capture after-state.
6. Write an audit event using the existing project audit framework.
7. Do not create a parallel/custom audit mechanism.
8. Ensure rollback removes the business change if audit/write fails where the project's audit transaction model requires that behavior.

### Verification

Test:

- authorized correction;
- unauthorized correction;
- correction of non-effective address;
- before/after audit contents;
- rollback.

---

## Step 13 — Verify Tenant Isolation and RLS Compatibility

### Gap

C-13 intentionally does not duplicate tenant/institution ownership columns on Address or AddressAssignment because scope is derived from the target entity.

However, the database/RLS behavior must be verified against the existing tenant architecture.

### Required Work

1. Inspect existing RLS strategy and session variables.
2. Determine how polymorphic C-13 records are protected through their target entity.
3. Verify C-13 does not bypass tenant isolation.
4. Verify Platform Owner behavior remains consistent with the architecture.
5. Ensure cross-client/cross-institution access is rejected.
6. Do not introduce a second tenant-context implementation.
7. Do not add redundant tenant columns merely to make RLS easier unless the architecture/ADR explicitly requires it.

### Verification

Run real database tests for:

- same institution;
- different institution;
- different client;
- Platform Owner;
- unauthorized user.

---

## Step 14 — Verify and Harden Migration/Database Constraints

### Gap

Migration `027_c13_address` creates the C-13 schema, but all required integrity constraints and project conventions need verification.

### Required Work

Review:

- primary keys;
- foreign keys;
- unique constraints;
- indexes;
- check constraints;
- nullable/non-nullable columns;
- delete behavior;
- timestamp behavior;
- compatibility tables;
- EntityType seed/reference data;
- geographic reference data;
- RLS/policy integration.

Do not redesign the schema unless a real PRD/architecture requirement is missing.

### Verification

- Fresh migration succeeds.
- Upgrade from the current project state succeeds.
- Downgrade behavior is understood and follows project conventions.
- Database constraints enforce critical invariants.

---

## Step 15 — Replace Weak Mock-Only C-13 Tests with Real DB/API Coverage

### Gap

`backend/tests/test_c13_address.py` relies heavily on `MagicMock(spec=Session)` and only covers a small subset of behavior.

This cannot verify actual:

- constraints;
- transactions;
- foreign keys;
- RLS;
- temporal behavior;
- route integration.

### Required Work

Keep unit tests where appropriate, but add integration coverage for real database behavior.

Minimum test groups:

1. Address validation.
2. Geographic hierarchy.
3. EntityType resolution.
4. AddressType compatibility.
5. Address creation.
6. Assignment creation.
7. Temporal overlap.
8. Effective/future/historical state.
9. Replacement.
10. Deletion.
11. Correction.
12. Authorization.
13. Tenant isolation.
14. Database uniqueness/integrity.
15. Transaction rollback.

### Verification

Run focused C-13 tests, then the full backend regression suite.

---

## Step 16 — Verify C-04 Authorization Integration

### Gap

C-13 defines permissions and role mappings, but authorization must be verified against the centralized C-04 decision flow.

### Required Work

1. Confirm C-13 does not implement its own authorization engine.
2. Confirm requests flow through the existing auth/authz middleware and C-04 decision process.
3. Verify permissions such as:
   - address.read
   - address.create
   - address.update
   - address.delete
   - address.correct
   - address_type.manage
4. Verify resource/tenant context is correctly supplied to authorization.
5. Review role mappings rather than broadly granting new access.

### Verification

Test allowed and denied operations for representative roles.

---

## Step 17 — Verify Geographic Reference Data Scope

### Gap

Migration 027 seeds Indian states and a set of cities.

The PRD needs to be reconciled with the actual intended geographic data scope.

### Required Work

1. Confirm whether the PRD requires all India states/UTs and what city coverage is expected.
2. Confirm state codes and country codes are stable.
3. Confirm city/state/country data is migration/seed managed.
4. Do not introduce runtime CRUD.
5. If current seed data is intentionally minimal, document that decision rather than silently expanding it.

### Verification

- Required reference data exists.
- Codes are stable.
- Hierarchy is valid.
- No runtime CRUD is exposed.

---

## Step 18 — Verify `updated_at` Behavior

### Gap

C-13 timestamp columns use database defaults, but update behavior needs to be checked against existing project conventions.

### Required Work

1. Inspect timestamp conventions in other kernel modules.
2. Confirm `updated_at` changes on updates where expected.
3. Ensure correction/replacement operations produce correct timestamps.
4. Align C-13 with existing project conventions instead of introducing a unique timestamp mechanism.

### Verification

Add a focused persistence test if necessary.

---

## Step 19 — Synchronize Documentation and Capability Status

### Gap

`AGENTS.md` capability tracking is stale relative to the actual repository state. It still indicates an older capability sequence even though C-06 Relationship and C-13 Address have been implemented.

### Required Work

1. Review the capability table in `AGENTS.md`.
2. Update only the status/order information that is demonstrably stale.
3. Do not alter architectural decisions without an ADR.
4. Ensure C-13 completion/gap-fill status is accurately represented.
5. If the project requires OpenSpec archival before moving forward, follow that process.

### Verification

Documentation reflects the actual implementation state.

---

# Recommended Implementation Order

Do not implement the gaps in arbitrary order.

Use this sequence because later steps depend on earlier foundations.

## Phase A — Make C-13 Actually Usable

1. **Step 1 — Application registration**
2. **Step 2 — EntityType resolution**
3. **Step 3 — AddressType resolution**
4. **Step 4 — Compatibility filtering**

## Phase B — Validate Address Data

5. **Step 5 — Geographic hierarchy**
6. **Step 6 — Field/whitespace validation**
7. **Step 17 — Geographic reference-data verification**

## Phase C — Protect Core Data Integrity

8. **Step 7 — Address ownership/no reuse**
9. **Step 14 — Migration/database constraints**
10. **Step 18 — `updated_at` behavior**

## Phase D — Complete Assignment Lifecycle

11. **Step 8 — Temporal assignment rules**
12. **Step 9 — Atomic replacement/move**
13. **Step 10 — Atomic deletion**

## Phase E — Complete Address Mutation Semantics

14. **Step 11 — Ordinary update rules**
15. **Step 12 — Effective correction + audit**

## Phase F — Security

16. **Step 13 — Tenant/RLS verification**
17. **Step 16 — C-04 authorization verification**

## Phase G — Verification & Documentation

18. **Step 15 — Real DB/API test coverage**
19. **Step 19 — Documentation/status synchronization**

---

# Definition of Done for C-13

C-13 should not be considered complete until all of the following are true:

- [ ] C-13 is registered in the application.
- [ ] EntityType resolution uses stable registered codes.
- [ ] AddressType resolution uses stable registered codes.
- [ ] AddressType compatibility is correctly enforced.
- [ ] Geographic hierarchy is enforced.
- [ ] Address field and whitespace rules are enforced.
- [ ] Address ownership is exclusive.
- [ ] Address cannot be reused.
- [ ] Assignment temporal rules are enforced.
- [ ] Historical/current/future states behave correctly.
- [ ] Replacement/move is atomic.
- [ ] Old addresses remain historical.
- [ ] Delete removes assignment + owned Address atomically.
- [ ] Ordinary update cannot bypass correction semantics.
- [ ] Effective correction requires `address.correct`.
- [ ] Correction produces proper before/after audit information.
- [ ] Tenant isolation is verified with real database tests.
- [ ] C-04 remains the sole authorization decision-maker.
- [ ] Critical database invariants are enforced at DB level where appropriate.
- [ ] Real integration tests cover the important C-13 workflows.
- [ ] Full regression tests pass.
- [ ] Import-linter/architecture checks pass.
- [ ] Migration checks pass.
- [ ] Documentation/status is synchronized.

---

# Suggested Workflow for Future Implementation Prompts

When implementing this plan, request one step at a time.

Example:

> Create the AI coding prompt for **Step 1 — Register C-13 in Application Composition**.

The implementation prompt should then be narrowly scoped to that step and should instruct the coding agent to:

- inspect before changing;
- verify the gap;
- follow existing project conventions;
- make minimal changes;
- add focused tests;
- run verification;
- report changed files and results;
- avoid fixing unrelated C-13 gaps.

After Step 1 is verified, move to Step 2, and so on.

---

# Important Guardrails

1. **Do not rebuild C-13.**
2. **Do not replace the existing architecture.**
3. **Do not introduce membership.**
4. **Do not create a second authorization mechanism.**
5. **Do not create a second tenant-context mechanism.**
6. **Do not add redundant tenant columns without architectural justification.**
7. **Do not modify unrelated modules merely for cleanup.**
8. **Do not perform broad refactoring while fixing an individual gap.**
9. **Do not mark a gap complete based only on mocked unit tests when database behavior is involved.**
10. **Do not start the next implementation step until the current step has been verified.**
11. **If implementation reveals a contradiction with the PRD/ADR/OpenSpec, stop and surface the contradiction instead of silently changing the design.**
12. **Prefer existing project patterns over introducing new abstractions.**

---

# Decisions Locked 2026-09-07 (Grill Session)

All implementation grill decisions from `2026-09-05` are now reflected in `docs/prd/C-13-Address-Management-PRD.md §24` and `docs/prd/c-13-impact-classification.md`.

| # | Decision | Gap Register Step |
|---|---:|---|
| D1 | Module `kernel/address/` (singular) | G-01 |
| D2 | Only 2 EntityTypes `INSTITUTION`, `PERSON` (Student/Employee via Person) | G-02 |
| D3 | Generic polymorphic `entity_type_id` + `entity_id` (Option A) | G-02/03 |
| D4 | No `client_id`/`institution_id` on `address`/`address_assignment` — scope derived from entity | G-13 |
| D5 | C-04 app-level authz, no RLS in Phase 1 | G-13 |
| D6 | Seed India geographic data (1 country, 28 states, 45 cities) — minimal intentional | G-17 |
| D7 | App-level temporal overlap validation | G-08 |
| D8 | Hard delete `AddressAssignment` + owned `Address` (no orphan, no reuse) + `UNIQUE(address_id)` | G-07/10 |
| D9 | Single transactional `replace_address()` (end old, create new Address, new assignment) | G-09 |
| D10 | Separate `address.correct` endpoint for effective addresses | G-11/12 |
| D11 | Composite unique codes: Country `code`, State `(country_id,code)`, City `(state_id,code)` | G-05/14 |
| D12 | Audit via existing `AuditEmitter` (`address.created/corrected/deleted` etc.) | G-12 |
| D13 | All routes in `kernel/address/routes/` (Option 1 refined): `addresses.py`, `person_addresses.py`, `institution_addresses.py`, `reference_data.py`, `address_types.py` | G-01 |
| D14 | `postal_code` **required** `VARCHAR(20) NOT NULL` — overrides PRD §7 `No` | G-06 |
| D15 | `locality`/`landmark` remain optional 100, blank→NULL | G-06 |

# Current Status

This document is a **gap register and implementation roadmap**, not an implementation prompt.

**2026-09-07:** Decisions D1-D15 locked. `postal_code required` decision applied to Step 6. PRD `§7` amendment pending docs-first commit per `AGENTS.md §3`.

The next action is **Step 6 docs-first PRD amendment** (`postal_code No → Yes`) then implementation per small-step rule.
