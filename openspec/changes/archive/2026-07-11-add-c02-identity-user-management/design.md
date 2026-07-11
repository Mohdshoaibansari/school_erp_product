## Context

C-02 (Identity & User Management) is the second-most depended-upon capability in the School ERP, after C-01 (Tenant & Institution Management). Every business module — Attendance, Fees, Homework, Exams, Timetable, Parent Communication, Leave Management, Transport, Events — references users. C-02 provides the unified user identity foundation that all these modules key off.

**C-02 is entirely Kernel (not Kernel\*).** User management is platform infrastructure, not business domain. No school administrator wants to "create users" — they want to take attendance and manage homework. User management is a prerequisite for business operations, not a business operation itself. Therefore, all C-02 code lives under `kernel/` (not `business/`), and C-02 does NOT produce a business domain module.

The `openspec/specs/` tree contains one existing spec: `tenant-institution/spec.md` (C-01). C-02 is a NEW domain — all requirements are ADDED. The decisional source of truth for this design is the grill-me session (11 locked decisions, 2026-07-08) and PRD `docs/prd/c-02-identity-user-management.md` (AC-1..AC-20).

C-02 follows the same architectural patterns established by C-01: module manifest (A5), TenantAwareRepositoryBase (A6), TenantContext (A6), service layer (A4), state machine, lifecycle events, lookup tables, RLS, DTOs, and AuditEmitter Protocol (C-11 boundary). C-02 does NOT modify C-01's behavioral spec.

**References:**
- Proposal: `openspec/changes/add-c02-identity-user-management/proposal.md`
- Spec: `openspec/changes/add-c02-identity-user-management/specs/identity-user-management/spec.md`
- PRD: `docs/prd/c-02-identity-user-management.md`
- Impact classification: `docs/prd/c-02-impact-classification.md`
- C-01 spec: `openspec/specs/tenant-institution/spec.md`
- C-01 design: `openspec/changes/archive/2026-07-08-add-c01-tenant-institution/design.md`
- C-01 tasks: `openspec/changes/archive/2026-07-08-add-c01-tenant-institution/tasks.md`
- Platform architecture ADR: `docs/architecture/adr-platform-software-architecture.md` (A1–A11)
- C-01 ADR: `docs/architecture/adr-c01-tenant-institution-implementation.md` (D1–D12)

## Goals / Non-Goals

**Goals:**
- Implement the C-02 entities: User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, UserLifecycleEvent
- Implement the User lifecycle state machine (Invited → Pending → Active → Suspended → Archived; Archived terminal)
- Implement tenant isolation for C-02 entities (client_id RLS + TenantAwareRepositoryBase)
- Implement module manifest registration (A5)
- Implement audit emission via AuditEmitter Protocol (C-11 boundary)
- Provide seed data for UserCategory and Role lookup tables
- Follow C-01's established patterns exactly (module structure, repo base, service layer, state machine, DTOs)

**Non-Goals:**
- Authentication (C-03) — C-02 stores users; C-03 verifies identity and issues JWTs
- Authorization/Casbin enforcement (C-04) — C-02 stores role assignments; C-04 enforces permissions
- Academic structure (C-05) — C-02 does not model subject assignments
- Student-parent relationships (C-06) — C-02 does not model family relationships
- Notifications (C-09) — C-02 does not send invitations or notifications
- Audit storage (C-11) — C-02 emits audit events; C-11 owns the immutable event log
- Code generation (C-12) — C-02 stores identifier values; C-12 generates them
- Cross-institution identity linking (Person table) — deferred to future phase
- Institution picker at login — each User has a unique email; login with that email → access that institution
- User transfer workflow — moving a user between institutions = archive old account + create new account
- Authorization enforcement — C-02 stores role assignments but does NOT enforce permissions

## Decisions

### Decision 1: No Person Table — User Per Institution

**Choice:** Each User record is per-institution. A person who works at two schools has two separate User accounts with two separate email addresses. There is NO Person table.

**Rationale:** Simplest model that avoids cross-institution linking complexity. Matches the real-world workflow where users log in to a specific institution. Multi-institution users are rare (directors, regional managers) and can maintain separate accounts.

**Alternatives considered:**
- Person + User (per-institution assignment) — more complex, requires Person-User relationship management
- Person + User (single User, multi-institution) — requires institution picker at login, more complex session management

### Decision 2: Unique Email Per User

**Choice:** Each User has a globally unique email address across the entire platform. No two User records (even across different Clients or Institutions) can share the same email.

**Rationale:** Simple authentication model. Login with specific email → access specific institution. No ambiguity about which account the email belongs to.

**Alternatives considered:**
- Email unique per institution — allows same email across institutions, but requires institution picker at login
- Email unique per client — allows same email across clients, but requires client selection at login

### Decision 3: Login Flow — Email Determines Institution

**Choice:** Login with a specific email → access to that email's institution only. No institution picker is shown. To access a different institution, the user logs out and logs back in with the other institution's email.

**Rationale:** Simplest authentication flow. No post-authentication picker needed. Each email maps to exactly one institution.

**Alternatives considered:**
- Post-authentication institution picker — more complex, requires Person linking
- JWT carries person_id + institution_id — requires Person table

### Decision 4: User Table Structure

**Choice:** User table fields: `id` (UUID v4), `client_id` (FK, RLS), `institution_id` (FK), `email` (globally unique), `name`, `user_category_id` (FK to lookup), `lifecycle_status`, `created_at`, `updated_at`.

**Rationale:** Follows C-01's field purity principle. Identity and lifecycle only. No profile fields (those go in UserProfile). No role fields (those go in RoleAssignment). No identifier fields (those go in UserIdentifier).

### Decision 5: UserProfile — Separate Table

**Choice:** UserProfile is a separate table linked 1:1 to User. Fields: `id` (UUID v4), `user_id` (FK), `photo`, `date_of_birth`, `gender`, `blood_group`. Optional — a User can exist without a UserProfile.

**Rationale:** Keeps the User table lean. Profile fields are optional and can grow independently. Follows C-01's pattern of separating identity from configuration.

### Decision 6: RoleAssignment — User + Role + Scope

**Choice:** RoleAssignment has `id` (UUID v4), `user_id` (FK), `role_id` (FK), `scope`. Institution comes from the User record — RoleAssignment does NOT store `institution_id`. A user can hold multiple RoleAssignments at the same institution.

**Rationale:** Clean separation. Role assignment is per-institution (via User.institution_id). Scope field allows flexible role coverage (e.g., "Mathematics Department" for HOD). No redundant institution_id.

### Decision 7: UserIdentifier — Institution-Scoped

**Choice:** UserIdentifier has `id` (UUID v4), `user_id` (FK), `type`, `value`. Institution comes from the User record — UserIdentifier does NOT store `institution_id`. Identifiers are unique per (institution, type, value) via User.institution_id.

**Rationale:** Same pattern as RoleAssignment. Institution is inferred from the User record. Unique constraint enforced via the User's institution_id.

### Decision 8: User Lifecycle — Archived Terminal

**Choice:** User lifecycle: `Invited → Pending → Active → Suspended → Archived`. Archived is terminal (no outgoing arcs). Allowed transitions: Invited→Pending, Pending→Active, Active→Suspended, Suspended→Active, Active→Archived, Suspended→Archived.

**Rationale:** Simple, clear lifecycle. Archived is permanent — no reactivation. To "restore" a user, create a new account. Follows C-01's terminated-is-terminal pattern for Clients.

### Decision 9: UserCategory — Lookup Table

**Choice:** UserCategory is a configurable lookup table. Default categories: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. Adding a new category is a data insert, not a code change.

**Rationale:** Follows C-01's pattern for configurable enums (legal_entity_type, org_unit_type, institution_type_name). No code changes needed to add categories.

### Decision 10: Role — Lookup Table

**Choice:** Role is a configurable lookup table. Default roles: Teacher, HOD, Principal, Student, Parent, Staff, Admin. Adding a new role is a data insert, not a code change.

**Rationale:** Same as Decision 9. Follows C-01's pattern for configurable enums.

### Decision 11: Full C-02 in Phase 1

**Choice:** Build all C-02 entities and features in Phase 1: User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, UserLifecycleEvent, lifecycle state machine, module manifest, audit emission, seed data.

**Rationale:** C-02 is a critical dependency for all business modules. Building it fully in Phase 1 unblocks Attendance, Fees, Homework, Exams, and other modules.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Profile duplication across institutions | Accepted per Decision 1. Multi-institution users are rare. Cross-institution identity linking is a future enhancement. |
| Email uniqueness constraint at platform level | Accepted per Decision 2. Each client controls their own email namespace. Conflicts across clients are extremely unlikely. |
| No automated user transfer between institutions | Accepted per Decision 8. Manual process (archive + create new) is acceptable for the rare multi-institution case. |
| RoleAssignment scope is free-text | Accepted for Phase 1. Scope validation against OrgUnit is a future enhancement (requires C-01 OrgUnit FK integration). |
| C-02 does not enforce authorization | Accepted per scope decision. C-02 stores role assignments; C-04 enforces permissions. Until C-04 is built, authorization is not enforced. |
| Lookup table seed data required | Seed data will be included in the Alembic migration (same pattern as C-01's lookup tables). |

## Open Questions

| # | Item | Disposition |
|---|---|---|
| OQ-1 | Cross-institution identity linking (Person table) | Deferred. Not needed for Phase 1. |
| OQ-2 | UserIdentifier value generation by C-12 | Deferred to C-12. C-02 accepts identifier values as input. |
| OQ-3 | RoleAssignment scope validation against OrgUnit | Deferred. Requires C-01 OrgUnit FK integration. |
| OQ-4 | User lifecycle approval flow | Deferred. Phase 1 lifecycle transitions are direct (no approval flow). |
| OQ-5 | UUID v7 revisit | Deferred. Same as C-01 OQ-5. |
| OQ-6 | User soft-delete vs hard-delete (GDPR) | Deferred. Phase 1 is archive-only. |
