## Why

Every business module in the School ERP needs to reference users: teachers who mark attendance, students who are marked present, parents who pay fees, principals who approve leave. Without a unified identity model, each module would invent its own user representation, leading to data duplication, inconsistent profiles, fragmented role management, and no single source of truth for "who is this person and what are they allowed to do at this institution."

C-02 provides the user identity foundation that every module keys off. It answers: who are the users of this institution, what category do they belong to (learner, teacher, staff), what roles do they hold (teacher, HOD, principal), and what identifiers are assigned to them (student ID, employee ID). C-02 is the second-most depended-upon capability after C-01 — every business module depends on both C-01 (tenant) and C-02 (users).

Key architectural decisions: no Person table (each User record is per-institution), unique email per User (login with specific email → access specific institution), and lookup tables for UserCategory and Role (configurable via data, not code).

## What Changes

- **NEW: User entity** — Per-institution user record with `client_id`, `institution_id`, `email` (unique), `name`, `user_category_id`, `lifecycle_status`. No Person table. Each User is a separate account per institution.
- **NEW: UserProfile entity** — Separate 1:1 table with extended profile fields: `photo`, `date_of_birth`, `gender`, `blood_group`. Optional — a User can exist without a UserProfile.
- **NEW: UserCategory lookup table** — Configurable classification: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. Adding a category is a data insert, not a code change.
- **NEW: Role lookup table** — Configurable assignment labels: Teacher, HOD, Principal, Student, Parent, Staff, Admin. Adding a role is a data insert, not a code change.
- **NEW: RoleAssignment entity** — User + Role + Scope. A user can hold multiple roles at the same institution (e.g., Teacher + HOD). `scope` field defines what the role covers (e.g., "Mathematics Department"). Institution comes from the User record.
- **NEW: UserIdentifier entity** — Institution-scoped business identifiers: Student ID, Employee ID, Admission Number. Typed, unique per (institution, type, value) via User.institution_id.
- **NEW: User lifecycle state machine** — `Invited → Pending → Active → Suspended → Archived`. Archived is terminal. Every transition records a lifecycle event (state, reason, actor) and is audited via C-11.
- **NEW: Module manifest registration** — C-02 registers via the ModuleManifest Protocol (A5). Routes registered via `register_routes`. Casbin policies registered via `register_casbin_policies` (no-op until C-04 is built).
- **NEW: Audit emission** — C-02 emits synchronous audit events via the AuditEmitter Protocol for: user creation, lifecycle transitions, role assignment/removal, identifier creation/deletion.

## Capabilities

### New Capabilities
- `identity-user-management`: User identity foundation — User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, User lifecycle state machine, tenant isolation, audit emission.

### Modified Capabilities
- None. C-02 does not modify C-01's behavioral spec. C-01's tenant isolation contract (D1) is followed by C-02 but not modified.

## Impact

- **New code:** `backend/business/identity_user_management/` (models, repos, routes, services, manifest, policies)
- **New migration:** `002_c02_identity_user_management.py` — User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, UserLifecycleEvent tables + RLS policies + seed data
- **Kernel dependencies:** C-02 inherits TenantAwareRepositoryBase, TenantContext, AuditEmitter from kernel (no kernel modifications)
- **Future consumers:** C-03 (Auth) will verify user identity and issue JWTs; C-04 (AuthZ) will enforce permissions via Casbin; C-09 (Notification) will consume user data for delivery; C-12 (Business Codes) will generate UserIdentifier values
- **Boundary declarations:** C-02 does NOT own authentication (C-03), authorization (C-04), academic structure (C-05), relationships (C-06), notifications (C-09), audit storage (C-11), or code generation (C-12)
