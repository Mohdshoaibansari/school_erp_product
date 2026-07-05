# Implementation Tasks — C-01 Tenant & Institution Management

> **Traceability.** Each task traces to ADR decision IDs (D1–D12, Q1–Q10) and PRD AC IDs (AC-1..AC-20). Tasks are grouped by concern and ordered by dependency. This is a checklist for the apply phase — no implementation is performed here.
>
> **Stack note (OPEN QUESTION — confirm before implementation).** No tech stack is chosen yet (no `package.json`, no code exists). The stack-dependent items below presume the POC-validated stack (Postgres + Supabase AuthN + Casbin AuthZ + RLS), but the parent must confirm the stack before the apply phase. Where the stack matters, the task notes "stack TBD." Stack-agnostic tasks describe the contract/evidence required regardless of stack.
>
> **References:** proposal.md, specs/tenant-institution/spec.md, design.md; ADR `docs/architecture/adr-c01-tenant-institution-implementation.md`; PRD `docs/prd/c-01-tenant-institution.md`.

## 1. Tech-stack confirmation (gating)

- [ ] 1.1 Confirm the tech stack with the parent before any implementation (stack TBD) — evidence: a recorded decision (doc or chat) naming the language/framework/ORM/DB. (OPEN QUESTION OQ-1; affects every stack-dependent task below.)
- [ ] 1.2 Confirm Postgres is the database backend (required for RLS per D1 and recursive CTE per D6). If a non-Postgres backend is chosen, escalate — D1 (RLS) and D6 (recursive CTE) must be reconsidered.

## 2. Database schema — C-01 entity tables (D2, D4, D5, D6, D7)

- [ ] 2.1 Create the `client` table with the D4 intrinsic fields (`id` UUID v4 PK, `slug` globally-unique immutable, `display_name`, `legal_name`, `legal_entity_type` FK to lookup table, `tax_registration_number`, contact fields, `address_id` FK → C-13, `current_lifecycle_status`, audit timestamps). No `client_id` column (the Client *is* the tenant, Q1). — evidence: migration file creating the table; a test asserting a Client row can be inserted with a UUID v4 id.
- [ ] 2.2 Create the `institution` table with the D5 intrinsic fields (`id` UUID v4 PK, `client_id` FK → client + RLS tenant column, `institution_type_id` FK immutable after creation, `display_name`, contact fields, `address_id` FK → C-13, `current_lifecycle_status`, affiliate fields, audit timestamps). — evidence: migration file; test asserting an Institution under a Client. (AC-17)
- [ ] 2.3 Create the `institution_type` table with the D7 intrinsic fields (`id` UUID v4 PK, `name` FK to lookup table per Q2, `code` unique, `is_system`, `default_org_unit_template` JSONB, audit timestamps). — evidence: migration file.
- [ ] 2.4 Create the `org_unit` table with the D6 intrinsic fields (`id` UUID v4 PK, `client_id` FK + RLS, `institution_id` FK default repo filter, `parent_id` self-FK nullable, `name`, `type` FK to lookup table per Q2 (immutable after creation), `sort_order`, `code` within-institution unique, `current_lifecycle_status`, audit timestamps). — evidence: migration file; test inserting a root OrgUnit and a child.

## 3. Database schema — lookup tables for configurable enums (Q2, AC-20)

- [ ] 3.1 Create lookup table `legal_entity_type` (`id`, `name`). — evidence: migration file; a test adding a new legal entity type via data insert with no code change (AC-20).
- [ ] 3.2 Create lookup table `org_unit_type` (`id`, `name`). — evidence: migration file; a test adding a new OrgUnit type via data insert (AC-20).
- [ ] 3.3 Create lookup table `institution_type_name` (`id`, `name`) for InstitutionType names. — evidence: migration file; a test adding a new InstitutionType name via data insert (AC-20).
- [ ] 3.4 Seed initial lookup data for legal entity types (e.g., Sole Proprietor / Partnership / Pvt Ltd / Trust / Society per D4) and OrgUnit types (Department / Faculty / Grade / Division / Section / Class / Program / Batch / Course per D6). — evidence: seed migration; test asserting seeded rows exist.

## 4. Database schema — lifecycle-event and ownership-transfer tables (D8, D9, D12, Q3)

- [ ] 4.1 Create `client_lifecycle_events` history table (`id` UUID v4, `client_id` FK, `state` entered, `entered_at`, `reason`, `actor`, FK to `Approval` if applicable per Q3). — evidence: migration file.
- [ ] 4.2 Create `institution_lifecycle_events` history table (`id` UUID v4, `client_id` + `institution_id` FKs, `state` entered, `entered_at`, `reason`, `actor`, FK to `Approval` if applicable). — evidence: migration file.
- [ ] 4.3 Create `ownership_transfer_events` table (`id` UUID v4, `from_client_id`, `to_client_id`, `institution_id`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason`, FK to `Approval`). — evidence: migration file. (AC-11)
- [ ] 4.4 Create the `approvals` table per Q3 (`id` UUID v4, `requested_by`, `approved_by`, `status`, `requested_at`, `approved_at`, context fields). — evidence: migration file; test creating a pending Approval row. (AC-19)

## 5. Database schema — RLS policies (D1, Q1, AC-1, AC-14)

- [ ] 5.1 Enable RLS and create a `client_id`-matching policy on every tenant-scoped C-01 table (`institutions`, `org_units`, `client_lifecycle_events`, `institution_lifecycle_events`, `ownership_transfer_events`). — evidence: migration file; a test where a Client-A query returns no Client-B rows. (AC-1)
- [ ] 5.2 Create the self-visible RLS policy on the `client` table: `id = current_client_id` (Q1). — evidence: migration file; a test where a Client Director reads only their own Client row, and where a Platform Owner reads all Clients. (AC-14)
- [ ] 5.3 Verify there is NO RLS policy on `institution_id` (it is a business filter, not a hard fence, per D1). — evidence: migration inspection; test that a cross-institution role can read across institutions within one client while Client boundary still holds. (AC-1)
- [ ] 5.4 Add a Platform Owner bypass/super_admin path for RLS (D11). — evidence: migration file; a test where Platform Owner reads all Clients/institutions across tenants.

## 6. Repository layer — tenant-aware data access (D1, Q6, AC-1, AC-9)

- [ ] 6.1 Implement tenant-aware repository base that injects `client_id` from TenantContext into every tenant-scoped query (business logic never passes `client_id`, never writes SQL). — evidence: a repository module; a test asserting a list query filters by `client_id` even when the caller omits it. (AC-1, ADR §5 constraint 1)
- [ ] 6.2 Implement the `institution_id` default business filter with cross-institution role override (Client Director etc. — D11). — evidence: a test where a Client Director reads across institutions within their client, and where a Client-A director cannot read Client-B data. (AC-1)
- [ ] 6.3 Implement OrgUnit cycle-prevention check in the repository before any parent-change update (Q6 — app-side; NO DB trigger). — evidence: a test where moving a node under its own descendant is rejected; a schema inspection asserting no DB trigger exists for cycle prevention. (AC-9)
- [ ] 6.4 Implement OrgUnit subtree-move semantics (the whole subtree moves with the node). — evidence: a test moving a subtree and asserting descendants retain relative structure. (AC-9)

## 7. API layer — subdomain resolution + endpoints (Q5, AC-12)

- [ ] 7.1 Implement subdomain → Client resolution middleware (the Client is implicit from the subdomain per D3; the c-01-explained `POST /api/clients/{slug}/institutions` form is superseded and MUST NOT be used). — evidence: middleware module; a test where `POST /api/v1/institutions` resolves the Client from the subdomain. (AC-12)
- [ ] 7.2 Implement the TenantContext (carries `client_id` + selected `institution_id` from JWT) plumbing. — evidence: module + test asserting the context carries both ids.
- [ ] 7.3 Implement Client CRUD + identity-update endpoints under the platform-scoped base (Platform-Owner-only per D11): create Client, identity update, lifecycle transitions. — evidence: API routes; tests covering AC-3 (slug rules/immutability), AC-13 (collision returns "taken"), AC-5 (Client lifecycle arcs). (AC-3, AC-13, AC-5, AC-15)
- [ ] 7.4 Implement Institution CRUD + identity-update endpoints under the client-portal subdomain base (subdomain-resolved per Q5): create Institution, identity update, lifecycle transitions, go-live (`Onboarding → Active`). — evidence: API routes; tests covering AC-6 (Institution lifecycle arcs), AC-7 (effective-state gating), AC-17 (field purity). (AC-6, AC-7, AC-12, AC-17)
- [ ] 7.5 Implement InstitutionType management endpoints (platform-scoped, Platform-Owner-only per D11): create/update InstitutionType with JSONB template. — evidence: API routes; test covering AC-16 (template materialization) and AC-20 (configurable via API). (AC-16, AC-20)
- [ ] 7.6 Implement OrgUnit endpoints (client-portal base, Institution/Admin scope per D11): create, move (cycle-prevented), archive, reactivate, reorder. — evidence: API routes; tests covering AC-8 (archive-only, type immutable), AC-9 (cycle-prevented move), AC-10 (move audited). (AC-8, AC-9, AC-10)
- [ ] 7.7 Implement ownership-transfer request/approval endpoints (platform-scoped, Platform-Owner-only per D12). — evidence: API routes; test covering AC-11 (single-transaction transfer) and AC-19 (approval flow). (AC-11, AC-19)

## 8. Lifecycle state machines + Approval flow (D8, D9, Q3, AC-5, AC-6, AC-7, AC-19)

- [ ] 8.1 Implement the Client lifecycle state machine (D8 arcs; `Terminated` terminal; `Archived` only re-activatable). Reject disallowed arcs. — evidence: state-machine module; tests for each allowed arc and rejection of `Terminated→Active`. (AC-5)
- [ ] 8.2 Implement the Institution lifecycle state machine (D9 arcs; no `Terminated`). Reject disallowed arcs. — evidence: state-machine module; test for each arc. (AC-6)
- [ ] 8.3 Implement runtime effective-state gating: an Institution is operationally Active only if its Client is Active — gated at runtime WITHOUT mutating the Institution row on transient Client suspension. — evidence: a test where suspending a Client gates an Active institution's access at runtime, then restoring the Client re-enables it with no persisted state restoration needed. (AC-7)
- [ ] 8.4 Implement the Approval flow (Q3): request creates a pending `Approval`; the dependent transition/transfer cannot complete until `status=approved`; `status=denied` blocks. — evidence: tests covering pending→approved completes; pending→denied blocks. (AC-19)
- [ ] 8.5 Wire every lifecycle transition to write a `client_lifecycle_events`/`institution_lifecycle_events` row with `state`, `entered_at`, `reason`, `actor`. — evidence: tests asserting the history row is written on each transition. (AC-5, AC-6)

## 9. OrgUnit hierarchy + move (D6, Q6, Q7, AC-8, AC-9, AC-10)

- [ ] 9.1 Implement OrgUnit archive-only deletion (soft-delete to `archived`) + reactivation; no hard-delete path. — evidence: a test where "delete" archives and reactivation restores `active`; a test asserting no hard-delete path exists. (AC-8)
- [ ] 9.2 Implement OrgUnit type immutability after creation. — evidence: a test where updating `type` is rejected. (AC-8)
- [ ] 9.3 Implement recursive CTE subtree/ancestor queries. — evidence: a query/test returning the full subtree of a node and the ancestor chain. (D6)
- [ ] 9.4 Implement OrgUnit move with cycle-prevention (Q6) + subtree moves + audit (Q7). — evidence: tests covering AC-9 (cycle-prevented) and AC-10 (audited as `org_unit_moved`); test asserting no dedicated `org_unit_move_event` table exists. (AC-9, AC-10)

## 10. InstitutionType template materialization (D7, AC-16)

- [ ] 10.1 Implement JSONB template validation at InstitutionType create/update: referenced OrgUnit types valid; tree acyclic. — evidence: tests rejecting invalid/acyclic templates. (D7)
- [ ] 10.2 Implement template materialization at Institution creation: OrgUnit rows matching the template are stamped with the new `client_id` + `institution_id` and correct `type`/`sort_order`. — evidence: a test creating an Institution and asserting the materialized OrgUnit tree. (AC-16)
- [ ] 10.3 Enforce InstitutionType immutability on an Institution after creation; force archive-and-recreate to "change" type. — evidence: a test rejecting `institution_type_id` update. (AC-16)
- [ ] 10.4 Verify InstitutionType does NOT drive runtime module behavior (Attendance/Fees/Homework/Exams operate identically). — evidence: a test (or note in the module behavior tests, once modules exist) asserting identical behavior across InstitutionTypes. (AC-16)

## 11. Ownership transfer transaction (D12, AC-11, AC-19)

- [ ] 11.1 Implement the transfer request + both-client consent + Platform Owner approval flow (Q3 Approval). — evidence: tests covering the approval flow blocking transfer until approved. (AC-11, AC-19)
- [ ] 11.2 Implement the single-transaction transfer updating `client_id` A→B across: Institution row, its OrgUnits, C-05 academic structure (coordinated with C-05, owned by C-05 — boundary), student records (C-02 scope), user-institution assignments (C-02 scope). — evidence: a test asserting all `client_id` columns are A→B after the transaction; a test asserting partial failure rolls back the entire transaction. (AC-11)
- [ ] 11.3 Implement post-move isolation verification (the Institution and dependent data are accessible only under Client B). — evidence: a test where Client A can no longer access the transferred Institution and Client B can. (AC-11)
- [ ] 11.4 Implement `OwnershipTransferEvent` recording (`from_client`, `to_client`, `institution`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason`). — evidence: a test asserting the event row is written. (AC-11)
- [ ] 11.5 Implement immutable-audit invariant: C-11 audit events recorded before the transfer keep their original ClientId. — evidence: a test where pre-transfer audit events are unchanged after the transfer. (AC-11, ADR §5 constraint 14)
- [ ] 11.6 Implement user migration rules: users whose only Institution is the transferred one migrate to Client B; users with other Client-A Institutions stay in Client A and lose the transferred Institution. (Coordinated with C-02, owned by C-02 — boundary.) — evidence: a test covering both user populations. (D12)
- [ ] 11.7 Note the billing-handoff coordination point (C-07/C-23 move subscription to Client B next billing cycle). This is a boundary declaration; C-07/C-23 own the billing behavior. — evidence: a code comment / coordination note + a test stub (the actual billing behavior is implemented in C-07/C-23's own change). (D12)

## 12. Permission matrix wiring (C-04 boundary) (D11, AC-15)

- [ ] 12.1 Encode the D11 tiered-delegation matrix as Casbin RBAC+ABAC policies (C-04 owns the framework; C-01 supplies the matrix content). — evidence: policy definitions + tests for each role: Platform Owner ALL; Client Director own-client (cannot mutate the Client); Institution Admin own-institution (cannot mutate the institution); cross-institution roles READ-only. (AC-15)
- [ ] 12.2 Verify cross-tenant writes (Client create/suspend/terminate, ownership transfer) are Platform-gated. — evidence: tests where a Client Director attempting these is rejected. (AC-15)
- [ ] 12.3 Verify all C-01 writes record actor identity via C-11. — evidence: tests asserting a C-11 audit event exists for each write. (AC-15)

## 13. Audit emission (C-11 boundary) (D8, D9, Q7, D12, AC-5, AC-6, AC-10, AC-11, AC-15)

- [ ] 13.1 Implement synchronous C-11 audit emission for Client lifecycle transitions (ClientId tagged). — evidence: a test asserting a C-11 event with ClientId on a transition. (AC-5)
- [ ] 13.2 Implement synchronous C-11 audit emission for Institution lifecycle transitions (ClientId + InstitutionId tagged). — evidence: a test asserting the event on a transition. (AC-6)
- [ ] 13.3 Implement C-11 audit emission for OrgUnit moves (generic `action="org_unit_moved"`, payload `{from_parent, to_parent, moved_by, ...}`). — evidence: a test asserting the event payload; assert no dedicated `org_unit_move_event` table. (AC-10)
- [ ] 13.4 Implement C-11 audit emission for ownership transfer + the immutability invariant across transfers. — evidence: tests as in 11.5. (AC-11)
- [ ] 13.5 Confirm no message broker / async event bus is introduced for C-01 (Q4 deferred). — evidence: codebase inspection asserting no broker integration; the emitter is synchronous. (Q4)

## 14. Boundary declarations (no cross-domain modifications) (D10, impact classification)

- [ ] 14.1 Verify C-01 has NO foreign key to C-05 (D10 zero-dependency invariant). — evidence: schema inspection test asserting no FK from any C-01 table to C-05 entities. (AC-18)
- [ ] 14.2 Verify `homeroom_teacher_id` is NOT a field on OrgUnit (it belongs to C-05 or C-02 RoleAssignment). — evidence: schema inspection test asserting the column's absence. (AC-18)
- [ ] 14.3 Verify tz/locale/currency/branding/`academic_year_start`/`grading_scale` are NOT intrinsic on Client or Institution (delegated to C-08). — evidence: schema inspection test asserting absence of those columns. (AC-17)
- [ ] 14.4 Verify no MODIFIED/REMOVED deltas exist for any other domain — every requirement is ADDED under `tenant-institution`. — evidence: inspection of `openspec/changes/add-c01-tenant-institution/specs/` confirming only `tenant-institution/spec.md` and only ADDED requirements.

## 15. Verification (gating apply → verify phase)

- [ ] 15.1 Run the OpenSpec verify phase (`openspec verify --change add-c01-tenant-institution`) once the apply phase lands the implementation. — evidence: verify output.
- [ ] 15.2 Run isolation tests covering AC-1 (cross-tenant data never visible) end-to-end. — evidence: test suite run with all isolation tests passing.
- [ ] 15.3 Confirm the c-01-explained supersede note — flag to the parent that `docs/platform-capabilities/c-01-tenant-institution-explained.md` should get a "Superseded by API contracts doc" note per Q5/PRD OQ-4 (this change does not edit `docs/`). — evidence: a note in the verify report.

## Open Questions (carried to apply)

- **OQ-1 — Tech stack** (see task 1.1): confirm language/framework/ORM/DB before any stack-dependent implementation. The design presumes Postgres + Supabase AuthN + Casbin AuthZ + RLS (POC-validated). A non-Postgres backend forces a D1/D6 reconsideration.
- **OQ-2 — `c-01-explained` supersede note** (see task 15.3): parent schedules a small follow-up `docs/` edit per PRD OQ-4 / Q5. Not blocking apply; not done by this change.
- **OQ-3 — OpenSpec-git-discipline**: per task constraints, the worker does not run git commits. The parent runs the openspec-git-discipline flow (proposal commit before apply; merge-before-archive) before `/opsx-apply`.
- **OQ-4 — Deferred ADR items** (no action now): Q4 (event bus), Q8 (lifecycle-event partitioning), Q10 (temporal/`client_id` history), D2 UUID v7, D12 watermark. Revisited only if a concrete requirement emerges (ADR §7).