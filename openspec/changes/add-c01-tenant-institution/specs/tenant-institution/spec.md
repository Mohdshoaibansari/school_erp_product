## ADDED Requirements

> **Traceability.** Each requirement below traces to one or more ADR decision IDs (D1–D12, Q1–Q10) and PRD acceptance criteria IDs (AC-1..AC-20) from `docs/architecture/adr-c01-tenant-institution-implementation.md` and `docs/prd/c-01-tenant-institution.md`. Decisional source of truth: the ADR. This is a NEW domain — every requirement is under the ADDED bucket.

### Requirement: Tenant Isolation Contract

The system SHALL enforce tenant isolation using a two-level hybrid model: (1) tenant-aware repositories as the data-access contract — business logic MUST NOT write SQL directly and MUST NOT rely on RLS as the primary filter (ADR §5 constraint 1, D1); and (2) Postgres Row-Level Security (RLS) as a defense-in-depth backstop that filters by `client_id` on every tenant-scoped table even if a repository method is bypassed (ADR §5 constraint 2, D1, AC-1).

The **Client** boundary (`client_id`) is the hard legal boundary enforced by RLS. The **Institution** boundary (`institution_id`) is a default business filter applied by repositories and overridable by authorized cross-institution roles (Client Director, Regional Manager, Group Academic Head, Finance Controller) — it MUST NOT be enforced in RLS (D1).

Every tenant-scoped C-01 table MUST carry a `client_id` column with an RLS policy that matches the JWT/TenantContext `client_id` (D1, AC-1). The `client` table itself has no `client_id` column (the Client *is* the tenant); its RLS policy is defined under the "Self-Visible Client RLS" requirement (Q1, AC-14).

Trace: D1, AC-1.

#### Scenario: Repository injects client_id on every tenant-scoped query
- **WHEN** business logic calls a tenant-aware repository method on any tenant-scoped C-01 table
- **THEN** the repository injects the `client_id` from the TenantContext into the query filter without the caller passing it explicitly, and the returned rows are scoped to that client

#### Scenario: RLS backstop blocks a bypassed repository
- **WHEN** a query reaches a tenant-scoped C-01 table without the correct `client_id` filter (e.g., a repository method that forgets to inject `client_id`, or direct SQL)
- **THEN** Postgres RLS on `client_id` filters the rows so that no row belonging to a different Client is visible or returned (AC-1)

#### Scenario: Cross-institution read override is honored at the repository layer, not RLS
- **WHEN** an authorized cross-institution role (e.g., Client Director) performs a read that legitimately spans institutions within the same Client
- **THEN** the repository omits or widens the `institution_id` default filter for that role, while the `client_id` RLS boundary remains enforced (institution_id is NOT in RLS) (D1)

#### Scenario: A user belonging to Client A can never see Client B data
- **WHEN** any request is processed with a TenantContext resolved to Client A
- **THEN** no row belonging to Client B is visible or editable through any C-01 API, repository method, or direct database access path (AC-1)

### Requirement: Entity Identifiers — UUID v4

All C-01 entities — Client, Institution, OrgUnit, InstitutionType, and every lifecycle/event entity (`client_lifecycle_events`, `institution_lifecycle_events`, `ownership_transfer_events`) — SHALL use UUID v4 as primary key (D2, AC-2). The system MUST NOT use autoincrement sequences. The system MUST NOT use C-12 (Code & Identifier Engine) generated codes for C-01 primary keys, preserving C-01's zero-dependency property (C-12 is institution-scoped and depends on C-01; using it for C-01 PKs would create a circular dependency) (D2).

Trace: D2, AC-2.

#### Scenario: UUID v4 on every C-01 primary key
- **WHEN** a new row is created in any C-01 entity table
- **THEN** its primary key is a UUID v4 value that is globally unique without central coordination (AC-2)

#### Scenario: No autoincrement sequences on C-01 tables
- **WHEN** the database schema for any C-01 entity is inspected
- **THEN** no SERIAL/BIGSERIAL/IDENTITY autoincrement column is used as the primary key (AC-2)

#### Scenario: C-12 codes are not used for C-01 PKs
- **WHEN** a C-01 entity is created
- **THEN** its primary key is independent of the C-12 engine; only human-readable institution-scoped business codes (Student ID, Employee ID, receipt numbers — owned by C-12 and C-02) may use C-12 (AC-2)

### Requirement: Client Subdomain Slug — Format, Uniqueness, Immutability

The subdomain identifies the **Client** (never the institution) and is set once at Client creation and is immutable thereafter (D3, AC-3, AC-4). Format: lowercase, 3–63 characters, `[a-z0-9-]`, must start and end with an alphanumeric character (D3). The slug is globally unique across all Clients. Reserved platform labels (`www`, `api`, `admin`, `app`, `mail`, `auth`, `platform`, `super`, etc.) MUST be rejected (D3). The display name is mutable (supports rebranding without changing the URL); the slug never changes (D3, AC-3). There are no per-institution subdomains — multi-institution Clients are served through the same Client portal subdomain and the active institution is chosen via an in-app institution switcher after login (D3, AC-4). Create-time slug collision returns a "taken" outcome with no auto-suffix and no near-match suggestions (D3, Q9, AC-13).

Trace: D3, Q9, AC-3, AC-4, AC-13.

#### Scenario: Valid slug accepted at creation
- **WHEN** a Client is created with a slug matching lowercase 3–63 chars `[a-z0-9-]`, alphanumeric at both ends, globally unique, and not a reserved name
- **THEN** the slug is persisted and is immutable for the lifetime of that Client (AC-3)

#### Scenario: Reserved slug rejected
- **WHEN** a Client is created with a slug in the reserved-name block (e.g., `www`, `api`, `admin`)
- **THEN** creation is rejected with a clear error and the caller must propose a different slug (AC-3)

#### Scenario: Format violations rejected
- **WHEN** a Client is created with a slug that is not lowercase, is shorter than 3 chars, longer than 63 chars, contains characters outside `[a-z0-9-]`, or does not start/end alphanumerically
- **THEN** creation is rejected (AC-3)

#### Scenario: Slug collision returns "taken" with no suggestions
- **WHEN** a Client is created with a slug that already exists on another Client
- **THEN** the system returns a "taken" outcome, performs no auto-suffixing, and produces no near-match suggestions; the caller must propose a new slug (AC-13)

#### Scenario: Slug immutability after creation
- **WHEN** any update is attempted on an existing Client's slug field
- **THEN** the update is rejected; the slug does not change (AC-3)

#### Scenario: Display name is mutable
- **WHEN** the Client's `display_name` is updated
- **THEN** the update succeeds and the slug (and thus the URL) is unaffected (AC-3)

#### Scenario: No per-institution subdomains
- **WHEN** a Client has multiple Institutions
- **THEN** all institutions are served through the same Client portal subdomain; the active institution is selected via the in-app institution switcher (AC-4)

### Requirement: Client Entity — Field Purity and Config Delegation

The Client entity SHALL carry only identity + legal-identity + contact + lifecycle + an `address_id` foreign key to C-13 (D4, AC-17). Intrinsic C-01-owned fields: `id` (UUID v4 per D2), `slug` (immutable, globally unique per D3), `display_name` (mutable), `legal_name`, `legal_entity_type` (configurable enum backed by a lookup table per Q2), `tax_registration_number` (optional), `primary_contact_email`, `primary_contact_phone`, `billing_contact_email`, `address_id` (FK → C-13), `current_lifecycle_status` (per D8), and audit timestamps (`created_at`, `updated_at`, `archived_at`) (D4).

The Client MUST NOT carry timezone, locale, currency, branding (`logo_url`, `brand_color`, `theme`), subscription state, or billing/contract/payment fields — these live in C-08 (Config), C-07 (Subscriptions), and C-23 (Billing) respectively (D4, AC-17). `legal_entity_type` is stored as a configurable enum via a lookup table, so adding a new legal entity type is a data insert, not a code change (Q2, AC-20).

Trace: D4, Q2, AC-17, AC-20.

#### Scenario: Client carries identity and lifecycle only
- **WHEN** the Client schema is inspected
- **THEN** it contains only identity, legal-identity, contact, lifecycle, address-FK, and audit-timestamp fields; no timezone/locale/currency/branding/subscription/billing columns are present (AC-17)

#### Scenario: Adding a new legal entity type requires no code/deploy
- **WHEN** an administrator adds a new legal entity type (e.g., a regional variant)
- **THEN** the addition is a data insert into the `legal_entity_type` lookup table, with no code change or redeploy (AC-20)

### Requirement: Client Lifecycle State Machine

The Client lifecycle SHALL implement the state machine defined in D8 (AC-5). States: `Prospective`, `Active`, `Suspended`, `Archived`, `Terminated`. Allowed transition arcs: `Prospective→Active` (contract signed + onboarding complete); `Prospective→Archived` (lead dropped); `Active→Suspended` (payment failure / policy violation / admin action); `Suspended→Active` (resolved + admin approval); `Active→Archived` (voluntary exit / contract end); `Archived→Active` (re-activation: contract renewed + admin approval); `Suspended→Archived` (escalation after grace); `Active→Terminated`, `Suspended→Terminated`, `Archived→Terminated` (permanent legal/financial closure) (D8, AC-5).

`Terminated` is **terminal** — no exit arcs. `Archived` is the only re-activatable inactive state (D8, AC-5). Every transition MUST record a reason and require Platform Owner approval via the Approval flow (Q3, AC-19), MUST record the actor, and MUST be audited via C-11 with the ClientId tagged (D8, AC-5). Each transition MUST be recorded in a `client_lifecycle_events` history table (`state`, `entered_at`, `reason`, `actor`) (D8).

Trace: D8, Q3, AC-5, AC-19.

#### Scenario: Allowed transition executed and audited
- **WHEN** a Platform Owner approves a `Prospective→Active` transition with a recorded reason and actor identity
- **THEN** the Client's `current_lifecycle_status` becomes `Active`, a `client_lifecycle_events` row is written, and a C-11 audit event tagged with the ClientId is emitted (AC-5)

#### Scenario: Disallowed arc rejected
- **WHEN** a transition is attempted that is not in the allowed arcs (e.g., `Terminated→Active`)
- **THEN** the transition is rejected and no state change occurs (AC-5)

#### Scenario: Terminated is terminal
- **WHEN** a Client is in `Terminated` and any outgoing transition is attempted
- **THEN** the transition is rejected; `Terminated` has no exit arcs (AC-5)

#### Scenario: Archived re-activation requires approval
- **WHEN** an `Archived→Active` re-activation is requested
- **THEN** it requires Platform Owner approval (Q3, AC-19) and a recorded reason before the Client returns to `Active` (AC-5)

#### Scenario: Transition without approval is blocked
- **WHEN** a transition requiring approval is attempted without an approved Approval record
- **THEN** the transition cannot complete until approval is granted (AC-19)

### Requirement: Approval Record Storage

The system SHALL provide a dedicated `Approval` table recording one row per approval: `requested_by`, `approved_by`, `status`, `requested_at`, `approved_at`, and relevant context (Q3, AC-19). The Approval flow supports a pending-approval state for lifecycle transitions (Client and Institution) and ownership transfer. A transition requiring approval MUST NOT complete until the corresponding Approval record is granted (Q3, AC-19).

Trace: Q3, AC-19.

#### Scenario: Approval requested and pending
- **WHEN** a lifecycle transition or ownership transfer requiring approval is initiated
- **THEN** an `Approval` row is created with `status=pending`, `requested_by` set to the initiator, and the operation cannot complete

#### Scenario: Approval granted completes the operation
- **WHEN** the approver grants the pending Approval
- **THEN** the `Approval` row transitions to `status=approved` with `approved_by` and `approved_at` set, and the dependent transition/transfer proceeds

#### Scenario: Approval denied blocks the operation
- **WHEN** the approver denies the pending Approval
- **THEN** the `Approval` row transitions to `status=denied`, and the dependent transition/transfer does not proceed

### Requirement: Institution Entity — Field Purity and Config Delegation

The Institution entity SHALL carry only identity + type-FK + contact + address-FK + lifecycle (D5, AC-17). Intrinsic C-01-owned fields: `id` (UUID v4 per D2), `client_id` (FK → Client; the RLS tenant column per D1), `institution_type_id` (FK → InstitutionType; immutable after creation per D7), `display_name` (mutable), `legal_name` (optional), `code` (optional, within-client unique short code), `primary_contact_email`, `primary_contact_phone`, `address_id` (FK → C-13), `current_lifecycle_status` (per D9), `established_year` (optional), `affiliation_number`/`affiliation_board` (optional, regional legal identity), and audit timestamps (`created_at`, `updated_at`, `archived_at`) (D5).

The Institution MUST NOT carry timezone, locale, currency, branding, `academic_year_start`, `grading_scale`, or any academic structure — these live in C-08 (Config) and C-05 (Academic structure) respectively (D5, AC-17). There is no per-institution subdomain (D3, AC-4).

Trace: D5, AC-17.

#### Scenario: Institution carries identity and lifecycle only
- **WHEN** the Institution schema is inspected
- **THEN** it contains only identity, type-FK, contact, lifecycle, address-FK, affiliation, and audit-timestamp fields; no timezone/locale/currency/branding/academic-structure columns are present (AC-17)

#### Scenario: Institution created under a Client
- **WHEN** a Client Director creates an Institution under their own Client
- **THEN** the Institution row is created with the Client's `client_id`, a chosen `institution_type_id`, and the default OrgUnit template from that InstitutionType is materialized (per the InstitutionType requirement)

### Requirement: Institution Lifecycle State Machine and Effective-State Gating

The Institution lifecycle SHALL implement the state machine defined in D9 (AC-6). States: `Onboarding`, `Active`, `Inactive`, `Archived` — **no `Terminated`** for institutions (that is Client-level only, D9, AC-6). Allowed transition arcs: `Onboarding→Active` (go-live: setup complete + admin approval); `Onboarding→Archived` (onboarding abandoned, never went live); `Active→Inactive` (pause: term break / seasonal closure / admin pause); `Inactive→Active` (resume + admin approval); `Active→Archived` (permanent closure, data retained); `Inactive→Archived` (escalation: inactive becomes permanent); `Archived→Active` (re-activation) (D9, AC-6).

Every transition MUST be audited via C-11 (ClientId + InstitutionId tagged) and recorded in an `institution_lifecycle_events` history table (D9, AC-6). Each transition requiring approval follows the Approval flow (Q3, AC-19).

Effective-state gating (AC-7): an Institution is operationally Active **only if** its Client is Active. If the Client enters `Suspended`, `Archived`, or `Terminated`, the Institution's access is gated at **runtime (effective state)** **without** the Institution row's lifecycle state being mutated — i.e., no cascade on transient Client suspension (D9, AC-7). Each institution's own lifecycle position is preserved; a briefly-suspended Client does not lose each institution's state.

Trace: D9, Q3, AC-6, AC-7, AC-19.

#### Scenario: Allowed institution transition executed and audited
- **WHEN** an `Onboarding→Active` transition is approved with admin approval
- **THEN** the Institution's `current_lifecycle_status` becomes `Active`, an `institution_lifecycle_events` row is written, and a C-11 audit event tagged with ClientId + InstitutionId is emitted (AC-6)

#### Scenario: No Terminated state for institutions
- **WHEN** the Institution state machine is inspected
- **THEN** the `Terminated` state does not exist for institutions; only Client-level lifecycle has `Terminated` (AC-6)

#### Scenario: Archived institution re-activatable
- **WHEN** an `Archived→Active` re-activation is requested and approved
- **THEN** the Institution returns to `Active` (D9, AC-6)

#### Scenario: Effective-state gates institution access when Client suspended
- **WHEN** the Client enters `Suspended` while an Institution's own state is `Active`
- **THEN** the Institution is not operationally Active at runtime (its access is gated), but its `current_lifecycle_status` row value is NOT mutated — no cascade (AC-7)

#### Scenario: Institution resumes operationally when Client reactivates
- **WHEN** the Client returns to `Active` (from `Suspended` or `Archived`)
- **THEN** the Institution becomes operationally Active again at runtime if its own lifecycle state is `Active`, with no persisted state restoration needed (AC-7)

#### Scenario: Client Terminated — institution permanently inaccessible
- **WHEN** the Client is `Terminated` (terminal)
- **THEN** the Institution is permanently inaccessible at runtime, but its row's lifecycle state is still not mutated (gating is effective/runtime, not persisted) (AC-7)

### Requirement: InstitutionType and Default OrgUnit Template Materialization

InstitutionType SHALL be configurable via API (not hardcoded in code or seed files), with intrinsic C-01-owned fields: `id` (UUID v4), `name` (e.g., School / College / University / Coaching Institute), `code` (unique short code), `is_system` (system-defined vs configurable), `default_org_unit_template` (JSONB nested tree of `{ org_unit_type, sort_order, children: [...] }`), and audit timestamps (`created_at`, `updated_at`) (D7, AC-16). The `name` is backed by a lookup-table-stored configurable enum (Q2, AC-20).

At Institution creation, the chosen InstitutionType's `default_org_unit_template` SHALL be **materialized** into actual OrgUnit rows stamped with the new Institution's `client_id` + `institution_id` (D7, AC-16). Validation logic ensures referenced OrgUnit types are valid and the template tree is acyclic (D7).

InstitutionType on an Institution is **immutable after creation** (setup-time only); to "change" the type, the Institution must be archived and a new one created (D7, AC-16). InstitutionType MUST NOT drive runtime module behavior — Attendance, Fees, Homework, Exams operate identically regardless of type (D7, AC-16).

Trace: D7, Q2, AC-16, AC-20.

#### Scenario: Template materialized at institution creation
- **WHEN** an Institution is created with a chosen InstitutionType that has a `default_org_unit_template`
- **THEN** OrgUnit rows matching the template tree are created, stamped with the new Institution's `client_id` + `institution_id`, with the correct `type` and `sort_order` per template node (AC-16)

#### Scenario: New InstitutionType added via API without code/deploy
- **WHEN** an administrator adds a new InstitutionType (e.g., "Polytechnic") via API with a template
- **THEN** it is available for selection at Institution creation with no code change or redeploy (D7, AC-20)

#### Scenario: Invalid/acyclic template rejected at creation
- **WHEN** an InstitutionType is created or updated with a template whose OrgUnit-type references are invalid or whose tree contains a cycle
- **THEN** creation/update is rejected by application-side validation (D7)

#### Scenario: InstitutionType immutable on an Institution after creation
- **WHEN** an update is attempted on an existing Institution's `institution_type_id`
- **THEN** the update is rejected; to change type, archive the Institution and create a new one (AC-16)

#### Scenario: InstitutionType does not drive runtime module behavior
- **WHEN** modules (Attendance, Fees, Homework, Exams) operate on institutions of different InstitutionTypes
- **THEN** their runtime behavior is identical regardless of the InstitutionType (AC-16)

### Requirement: OrgUnit Hierarchy and Restructuring Rules

OrgUnit hierarchy SHALL use an adjacency-list model (`parent_id` self-FK on OrgUnit, nullable = root) with Postgres recursive CTE (`WITH RECURSIVE`) for subtree/ancestor queries (D6). OrgUnit intrinsic C-01-owned fields: `id` (UUID v4), `client_id` (FK → Client; RLS tenant column per D1), `institution_id` (FK → Institution; default repo filter per D1), `parent_id` (FK → OrgUnit, nullable), `name`, `type` (configurable enum via lookup table per Q2; immutable after creation per D6), `sort_order`, `code` (optional, within-institution unique), `current_lifecycle_status` (`active`/`inactive`/`archived`), and audit timestamps (D6, AC-8).

Deletion is **archive-only** (soft-delete with reactivation allowed); there is no hard-delete path (D6, AC-8). The OrgUnit `type` is **immutable after creation** — to "change" type, archive the node and create a new one (D6, AC-8).

Moving an OrgUnit (parent change) is allowed, **audited**, **cycle-prevented**, and the whole subtree moves with the node (D6, AC-9). Cycle prevention is enforced **on the application/repository side**; the database schema MUST NOT add a duplicating trigger (Q6, AC-9). Every move is audited via C-11 as a generic audit event `action="org_unit_moved"` with `payload={from_parent, to_parent, moved_by, ...}` — there is no dedicated `org_unit_move_event` table (Q7, AC-10).

Trace: D6, Q2, Q6, Q7, AC-8, AC-9, AC-10.

#### Scenario: Archive-only deletion with reactivation
- **WHEN** an OrgUnit is "deleted" by an Institution Admin
- **THEN** the OrgUnit is soft-deleted (`current_lifecycle_status` becomes `archived`); there is no hard-delete path; an archived OrgUnit can be reactivated to `active` (AC-8)

#### Scenario: OrgUnit type immutable after creation
- **WHEN** an update is attempted on an existing OrgUnit's `type`
- **THEN** the update is rejected; to change type, archive the node and create a new one (AC-8)

#### Scenario: Move is cycle-prevented on the application side
- **WHEN** an attempt is made to move an OrgUnit under one of its own descendants
- **THEN** the repository-side check rejects the move before the database update; no cycle is created (AC-9)

#### Scenario: No DB-level cycle-prevention trigger
- **WHEN** the OrgUnit schema is inspected
- **THEN** there is no database trigger duplicating the cycle-prevention logic; all cycle prevention flows through the repository (Q6, AC-9)

#### Scenario: Subtree moves with the node
- **WHEN** an OrgUnit with descendants is moved to a new parent
- **THEN** the entire subtree (all descendants) moves with the node, retaining their relative structure (AC-9)

#### Scenario: Move is audited as a generic org_unit_moved event
- **WHEN** an OrgUnit is moved to a new parent
- **THEN** a C-11 audit event with `action="org_unit_moved"` and `payload={from_parent, to_parent, moved_by, ...}` is emitted; no dedicated `org_unit_move_event` table is created (Q7, AC-10)

#### Scenario: Recursive CTE retrieves subtree
- **WHEN** a subtree or ancestor query is performed on the OrgUnit hierarchy
- **THEN** the system uses a Postgres recursive CTE over the adjacency-list `parent_id` relation to resolve the tree (D6)

### Requirement: OrgUnit Purity — C-05 Academic Boundary

OrgUnit SHALL be a pure structural/administrative container carrying only structural fields (`id`, `client_id`, `institution_id`, `parent_id`, `type`, `name`, `code`, `sort_order`, `lifecycle`) with **no academic metadata** (D10, AC-18). Grade/Class/Section/Program/Batch are OrgUnit *types* owned by C-01 (D10). AcademicYear, Term, Subject, class-subject mapping, homeroom-teacher assignment are owned by **C-05** (Academic Structure).

C-05 entities hold foreign keys to C-01 OrgUnits (and Institution). C-01 MUST NOT have any foreign key to C-05 — this preserves C-01's zero-dependency property (D10, AC-18). The `homeroom_teacher_id` MUST NOT be a field on OrgUnit; it belongs to C-05 (academic assignment) or C-02 RoleAssignment scoped to OrgUnit + AcademicYear (D10, AC-18). A "class" used by Attendance/Exams is an OrgUnit (structural container) plus its C-05 academic metadata for the current academic year (D10).

Trace: D10, AC-18.

#### Scenario: OrgUnit has no academic metadata
- **WHEN** the OrgUnit schema is inspected
- **THEN** it contains only structural fields; no AcademicYear/Term/Subject/homeroom-teacher columns are present (AC-18)

#### Scenario: C-01 has no FK to C-05
- **WHEN** the C-01 schema is inspected for foreign keys to C-05 entities
- **THEN** no such foreign key exists; the FK direction is C-05 → C-01 only (AC-18)

#### Scenario: homeroom_teacher_id is not on OrgUnit
- **WHEN** the OrgUnit schema is inspected
- **THEN** `homeroom_teacher_id` is not present; it belongs to C-05 or C-02 RoleAssignment scoped to OrgUnit + AcademicYear (AC-18)

### Requirement: API Shape — Subdomain-Resolved

C-01 APIs SHALL be subdomain-resolved: the Client is implicit from the subdomain (per D3), not embedded in the request path (Q5, AC-12). The illustrative client-in-path form (`POST /api/clients/{slug}/institutions`) shown in `docs/platform-capabilities/c-01-tenant-institution-explained.md` is SUPERSEDED by the subdomain-resolved form — it MUST NOT be used (Q5, AC-12).

Platform-Owner-only endpoints (Client create/suspend/terminate, ownership-transfer approval, InstitutionType management) SHALL live under a platform-scoped base (Q5, AC-12). The JWT/TenantContext carries both `client_id` (resolved from the subdomain at request start, via C-03) and a selected `institution_id` (set by the in-app institution switcher after login) per D1.

Trace: Q5, D1, AC-12.

#### Scenario: Institution creation is subdomain-resolved
- **WHEN** an authorized user creates an Institution under their Client
- **THEN** the request is `POST /api/v1/institutions` with the Client implicit from the subdomain; the Client is not embedded in the path (AC-12)

#### Scenario: Platform-Owner-only endpoints under a platform-scoped base
- **WHEN** a Platform Owner performs Client create/suspend/terminate, ownership-transfer approval, or InstitutionType management
- **THEN** those endpoints live under a platform-scoped base distinct from the client-portal subdomain base (AC-12)

#### Scenario: Superseded client-in-path form is not used
- **WHEN** the API surface is designed or documented
- **THEN** the `POST /api/clients/{slug}/institutions` form is not used; the subdomain-resolved `POST /api/v1/institutions` form is authoritative (Q5, AC-12)

### Requirement: C-01 Write-Permission Matrix

The system SHALL enforce the tiered delegation write-permission matrix defined in D11 for every C-01 mutation (AC-15). **Platform Owner** (SaaS provider side, all tenants): ALL C-01 operations — create/suspend/archive/terminate Client, manage InstitutionTypes, approve ownership transfers, and any lower-tier operation as higher authority. **Client Director** (own client only): create institution; activate/inactive/archive/reinstate institution; update Client + Institution identity; manage OrgUnits. **Cannot** create/suspend/terminate the Client itself (must request Platform Owner). **Institution Admin / Principal** (own institution only): update institution identity; create/move/archive/reactivate OrgUnits. **Cannot** create/suspend/archive the institution itself. **Cross-institution roles** (Regional Manager, Group Academic Head, Finance Controller, across institutions within a client): READ-only oversight on C-01; no C-01 write operations (D11, AC-15).

All writes MUST be audited via C-11 with actor identity (D11, AC-15). Casbin RBAC+ABAC encodes this matrix at the API layer (C-04 owns the framework); RLS enforces `client_id` isolation at the DB layer as the backstop (D11, AC-15). Cross-tenant write operations (Client create/suspend/terminate, ownership transfer) require Platform Owner approval (D11, D12, AC-15).

Trace: D11, AC-15.

#### Scenario: Platform Owner can perform all C-01 operations
- **WHEN** a Platform Owner performs any C-01 operation (create/suspend/archive/terminate Client, manage InstitutionTypes, approve transfer)
- **THEN** the operation is permitted and is audited via C-11 with the Platform Owner as actor (AC-15)

#### Scenario: Client Director manages own-client institutions but not the Client itself
- **WHEN** a Client Director creates an institution or updates Client/Institution identity within their own Client
- **THEN** the operation is permitted
- **AND WHEN** the same Client Director attempts to create/suspend/terminate the Client itself
- **THEN** the operation is rejected; it requires Platform Owner approval (AC-15)

#### Scenario: Institution Admin manages own-institution OrgUnits but not the institution itself
- **WHEN** an Institution Admin creates/moves/archives OrgUnits within their own institution
- **THEN** the operation is permitted
- **AND WHEN** the same Institution Admin attempts to create/suspend/archive the institution itself
- **THEN** the operation is rejected; it requires Client Director action (AC-15)

#### Scenario: Cross-institution roles are read-only on C-01
- **WHEN** a cross-institution role (Regional Manager, Group Academic Head, Finance Controller) attempts any C-01 write operation
- **THEN** the operation is rejected; cross-institution roles have READ-only oversight on C-01 (AC-15)

#### Scenario: All C-01 writes record actor identity via C-11
- **WHEN** any permitted C-01 write is executed
- **THEN** a C-11 audit event is emitted recording the actor identity (AC-15)

### Requirement: Institution Ownership Transfer

Institution ownership transfer SHALL be a Platform-Owner-approved **full operational transfer** with **immutable audit** (D12, AC-11). Workflow: (1) request initiated; (2) both source and destination Clients consent (legal/contractual); (3) Platform Owner approves (cross-tenant boundary change — neither side can self-serve); (4) execute in a **single transaction** with isolation verified post-move; (5) record an `OwnershipTransferEvent` (D12, AC-11).

The single transaction SHALL update `client_id` A→B across: the Institution row; its OrgUnits; C-05 academic structure for that institution; student records (C-02 scope); and user-institution assignments for that institution (C-02 scope) (D12, AC-11). Partial failure MUST roll back the entire transaction (D12). Audit events (C-11) created before the transfer MUST remain **immutable** under their original ClientId (historical truth preserved across the transfer) (D12, AC-11, ADR §5 constraint 14).

`OwnershipTransferEvent` captures: `from_client`, `to_client`, `institution`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason` (D12).

Users whose **only** Institution is the transferred one are migrated to Client B; users with other Client-A Institutions stay in Client A and lose the transferred Institution (C-02 coordination point — C-01 states the migration contract; C-02 owns the user entity) (D12). Billing (C-07/C-23) moves the Institution's subscription to Client B's invoice effective the next billing cycle (billing-handoff coordination point — C-01 notes it; C-07/C-23 own billing behavior) (D12).

C-01 owns the transfer **workflow** and its `OwnershipTransferEvent` record; the schema/behavior for the downstream tables (C-05, C-02) belongs to their respective capabilities' specs. C-01's spec describes the transfer as an explicit orchestration with named downstream coordination points (boundary declaration, not a cross-domain modification).

Trace: D12, Q3, AC-11, AC-19, ADR §5 constraint 14.

#### Scenario: Transfer requires Platform Owner approval and both-client consent
- **WHEN** an ownership transfer is requested
- **THEN** both source and destination Clients must consent and a Platform Owner must approve via the Approval flow (Q3, AC-19) before the transfer executes (AC-11)

#### Scenario: Transfer executes in a single transaction with rollback
- **WHEN** an approved transfer is executed
- **THEN** the Institution row, its OrgUnits, C-05 academic structure, student records, and user-institution assignments have `client_id` updated A→B in a single transaction; if any part fails, the entire transaction rolls back (AC-11)

#### Scenario: Isolation verified post-move
- **WHEN** the single-transaction transfer completes
- **THEN** isolation is verified post-move — the Institution and its dependent data are accessible only under Client B and not under Client A (AC-11)

#### Scenario: Audit events remain immutable across the transfer
- **WHEN** the transfer completes
- **THEN** C-11 audit events recorded before the transfer keep the ClientId they were recorded with (historical truth preserved); they are not rewritten to Client B (AC-11, ADR §5 constraint 14)

#### Scenario: OwnershipTransferEvent recorded
- **WHEN** the transfer completes
- **THEN** an `OwnershipTransferEvent` row is written capturing `from_client`, `to_client`, `institution`, `approved_by`, `consent_source`, `consent_dest`, `transferred_at`, `reason` (AC-11)

#### Scenario: User migration rules applied
- **WHEN** the transfer completes
- **THEN** users whose only Institution is the transferred one are migrated to Client B; users with other Client-A Institutions stay in Client A and lose the transferred Institution (D12)

#### Scenario: Billing handoff effective next cycle
- **WHEN** the transfer completes
- **THEN** the Institution's subscription moves to Client B's invoice effective the next billing cycle (C-07/C-23 coordination point; C-01 notes the handoff, C-07/C-23 own the billing behavior) (D12)

### Requirement: Configurable Enums Backed by Lookup Tables

Configurable enums — including Client `legal_entity_type`, OrgUnit `type`, and InstitutionType `name` — SHALL be backed by lookup tables (`legal_entity_type`, `org_unit_type`, `institution_type_name`) stored as `id` + `name` and FK-referenced by the entity tables (Q2, AC-20). Adding a new enum value is a **data insert**, with no code change and no redeploy (Q2, AC-20). This honors D7's "configurable, not hardcoded" rule (Q2).

Trace: Q2, D7, AC-20.

#### Scenario: New enum value added via data insert
- **WHEN** a new value is needed for `legal_entity_type`, OrgUnit `type`, or InstitutionType `name`
- **THEN** the addition is a data insert into the corresponding lookup table, with no code change or redeploy (AC-20)

#### Scenario: Entities FK-reference the lookup tables
- **WHEN** the Client/Institution/OrgUnit/InstitutionType schemas are inspected
- **THEN** their enum fields are FK-referenced to the corresponding lookup table, not hardcoded check constraints (AC-20)

### Requirement: Self-Visible Client RLS

The `client` table has no `client_id` column because the Client **is** the tenant (Q1, AC-14). The RLS policy on the `client` table itself SHALL be **self-visible**: a Client Director can read their own Client row via `id = current_client_id`, where `current_client_id` is resolved from the JWT/TenantContext (Q1, AC-14). Platform Owners can read all Clients (D11). No Client can read another Client's row (D1, AC-1).

Trace: Q1, AC-14, D1, AC-1.

#### Scenario: Client Director reads own Client row
- **WHEN** a Client Director resolved to Client A requests the Client record
- **THEN** the RLS policy `id = current_client_id` returns only Client A's row; Client B's row is not visible (AC-14)

#### Scenario: Platform Owner reads any Client row
- **WHEN** a Platform Owner requests any Client record
- **THEN** the operation is permitted per D11 (all C-01 operations) (AC-14)

#### Scenario: Client cannot read another Client's row
- **WHEN** a Client Director resolved to Client A attempts to read Client B's row
- **THEN** the attempt is filtered by RLS and Client B's data is not returned (AC-1, AC-14)

### Requirement: Capability Boundary Declarations

C-01 SHALL record all cross-capability boundary relationships as part of its own spec, and SHALL NOT issue MODIFIED/REMOVED deltas against any other capability's domain. These are interface dependencies and boundary declarations, NOT modifications to other domains' specs. The other domains will define their own sides of these boundaries in their own future change specs. C-01 is the zero-dependency (Level 1) root capability; every referenced capability depends on C-01, not the reverse (impact classification boundary table, ADR §4.1).

| C-01 relationship | Direction | Other capability | Nature |
|---|---|---|---|
| Client owns users' client context; user-institution assignments migrate on ownership transfer | C-01 → C-02 | C-02 (Users) | Boundary / coordination point |
| Auth resolves Client via subdomain; JWT carries `client_id` + selected `institution_id` | C-01 → C-03 | C-03 (Auth) | Boundary / interface dependency |
| C-04 encodes the D11 matrix as Casbin RBAC+ABAC policies | C-01 → C-04 | C-04 (AuthZ framework) | Boundary / first-cut matrix |
| C-05 holds FKs to C-01 OrgUnit and Institution; C-01 has NO FK to C-05 | C-05 → C-01 | C-05 (Academic structure) | Boundary / FK direction |
| Subscription gates modules at Client level; C-01 exposes Client identity | C-01 → C-07 | C-07 (Subscriptions) | Boundary / identity exposure |
| Config inherits Platform→Client→Institution→Module | C-01 → C-08 | C-08 (Config) | Boundary / config delegation |
| C-11 audit events tagged with ClientId (+ InstitutionId); C-01 emits/retains lifecycle history; audit is immutable across transfers | C-01 → C-11 | C-11 (Audit) | Boundary / consumer |
| C-12 reserved for institution-scoped business codes; not used for C-01 PKs (circular dependency avoidance) | C-01 → C-12 | C-12 (Business codes) | Boundary / avoidance contract |
| C-01 holds an address FK to C-13 | C-01 → C-13 | C-13 (Address) | Boundary / FK holder |
| Billing issues one invoice per Client, itemized per-Institution; transfer moves subscription to Client B next cycle | C-01 → C-23 | C-23 (Billing) | Boundary / coordination point |

Downstream coordination points (D12 ownership transfer's updates to C-05/C-02 tables, C-07/C-23 billing handoff, C-11 audit emission) are described in C-01's spec as C-01's orchestration contract and event-emission contract, with explicit "coordinated with \<capability\>, owned by \<capability\>" annotations (impact classification recommendation).

Trace: impact-classification boundary table, ADR §4.1, ADR §5 constraints 11–14, D10, D11, D12.

#### Scenario: Boundary relationships recorded in C-01's own spec only
- **WHEN** the C-01 change is inspected for cross-domain modifications
- **THEN** no MODIFIED deltas exist for any other domain; all boundary relationships are recorded as C-01's own boundary declarations within the `tenant-institution` spec

#### Scenario: C-01 emits C-11 audit events tagged with ClientId + InstitutionId
- **WHEN** a C-01 lifecycle transition, OrgUnit move, or ownership transfer occurs
- **THEN** C-01 emits a synchronous C-11 audit event tagged with ClientId and (where applicable) InstitutionId; C-11 owns the immutable event log (boundary / consumer) (ADR §5 constraint 14)

#### Scenario: C-01 delegates config to C-08
- **WHEN** timezone/locale/currency/branding/academic-year-start/grading-scale values are needed for a Client or Institution
- **THEN** they are served by C-08 (Config) via Platform→Client→Institution→Module inheritance; C-01 carries no such intrinsic columns (D4, D5, AC-17)

#### Scenario: Cross-tenant write operations require Platform Owner approval
- **WHEN** a cross-tenant boundary change is requested (Client create/suspend/terminate, ownership transfer)
- **THEN** it requires Platform Owner approval (D11, D12, ADR §5 constraint 13)