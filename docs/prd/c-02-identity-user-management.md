# PRD — C-02 Identity & User Management

> **Capability:** C-02 Identity & User Management
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-07-08
> **Decisional source of truth:** Grill-me session (11 locked decisions, 2026-07-08)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-02; `docs/architecture/architecture-v1.md` §5, §6, §6.1; `docs/architecture/adr-platform-software-architecture.md` (A2–A7); `docs/architecture/adr-c01-tenant-institution-implementation.md` (D1–D12 — patterns C-02 follows)
> **Scope note:** This is a **product** requirements document. Implementation detail (DB columns, API shapes, RLS policy text) belongs in the spec/design phase. Decisions are referenced by their grill-me number (e.g., "per Decision 1") rather than re-specified here.

---

## 1. Problem

Every business module in the School ERP — Attendance, Fees, Homework, Exams, Timetable, Parent Communication, Leave Management, Transport, Events — needs to reference **users**: teachers who mark attendance, students who are marked present, parents who pay fees, principals who approve leave, staff who manage transport. Without a unified identity model, each module would invent its own user representation, leading to data duplication, inconsistent profiles, fragmented role management, and no single source of truth for "who is this person and what are they allowed to do at this institution."

C-02 provides the **user identity foundation** that every module keys off. It answers: who are the users of this institution, what category do they belong to (learner, teacher, staff), what roles do they hold (teacher, HOD, principal), and what identifiers are assigned to them (student ID, employee ID). C-02 is the second-most depended-upon capability after C-01 — the dependency matrix shows every business module depends on both C-01 (tenant) and C-02 (users).

The key architectural decision that shaped this PRD: **no Person table** — each user record is per-institution. A teacher who works at two schools has two separate user accounts with two separate email addresses. This is the simplest model that avoids cross-institution linking complexity while matching the real-world workflow where users log in to a specific institution.

---

## 2. Goals & Non-goals

### 2.1 In scope — C-02 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **User** (a person with a platform identity at a specific institution) | Decision 1, 4 | Per-institution record. `client_id` + `institution_id` + `email` (unique) + `name` + `user_category_id` + `lifecycle_status`. No Person table. |
| **UserProfile** (extended profile fields) | Decision 5 | Separate table: `photo`, `date_of_birth`, `gender`, `blood_group`. 1:1 with User. |
| **UserCategory** (configurable classification) | Decision 9 | Lookup table: Learner, Academic Staff, Academic Leadership, Administrative Staff, Executive Leadership. Adding a category is a data insert, not a code change. |
| **Role** (configurable assignment label) | Decision 10 | Lookup table: Teacher, HOD, Principal, Student, Parent, Staff, Admin. Adding a role is a data insert, not a code change. |
| **RoleAssignment** (User + Role + Scope) | Decision 6 | A user can hold multiple roles at the same institution (e.g., Teacher + HOD). `scope` field defines what the role covers (e.g., "Mathematics Department"). Institution comes from the User record. |
| **UserIdentifier** (institution-scoped business identifiers) | Decision 7 | Student ID, Employee ID, Admission Number. Typed, institution-scoped. Unique per (institution, type, value) via User.institution_id. |
| **User lifecycle** (traceable state machine) | Decision 8 | Invited → Pending → Active → Suspended → Archived. Archived is terminal. Every transition is audited via C-11. |
| **Tenant isolation** | Per architecture A3, A6 | User table has `client_id` with RLS policy. Repositories inherit TenantAwareRepositoryBase. |

### 2.2 Out of scope — owned by other capabilities

| Concern | Owned by | Notes |
|---|---|---|
| Authentication (JWT, login, sessions, OTP) | C-03 | C-02 stores the user; C-03 verifies their identity and issues tokens. Login with specific email → access specific institution (Decision 3). |
| Authorization framework (Casbin, RBAC, ABAC, permission matrix) | C-04 | C-02 stores role assignments; C-04 enforces what those roles can do. C-04 will consume C-02's RoleAssignment table. |
| Academic structure (AcademicYear, Term, Subject, class-subject mapping) | C-05 | C-02 does not model academic assignments. A teacher's subject assignment is C-05. |
| Student-parent/guardian relationships | C-06 | C-02 does not model "this student has this parent." That is C-06 Relationship Management. |
| Audit framework (append-only event store) | C-11 | C-02 emits audit events via the AuditEmitter Protocol (C-11 boundary); C-02 does not own the audit store. |
| Human-readable business codes generation | C-12 | UserIdentifier values (Student ID, Employee ID) are generated by C-12. C-02 stores them. |
| Notification (email, SMS, push) | C-09 | C-02 does not send invitations or notifications. C-09 consumes C-02 user data for delivery. |

### 2.3 Explicit non-goals for Phase 1

- **No Person table** — each User record is per-institution. A person at two schools has two accounts (Decision 1). Cross-institution identity linking is a future enhancement if needed.
- **No institution picker at login** — each User has a unique email; login with that email → access that institution (Decision 3). No multi-institution session switching.
- **No Transferred lifecycle state** — moving a user between institutions = archive old account + create new account (Decision 8). No automated transfer workflow.
- **No authorization enforcement** — C-02 stores role assignments but does NOT enforce permissions. C-04 will add Casbin enforcement.
- **No authentication** — C-02 does not handle login, passwords, JWT, sessions, or OTP. C-03 owns that.
- **No student-parent relationships** — C-06 owns relationship management.
- **No configurable role definition** — Phase 1 uses system-defined roles (Teacher, HOD, Principal, Student, Parent, Staff, Admin). Configurable role definition is deferred.
- **No multi-institution users** — a user at two schools has two separate accounts with separate emails. No shared session across institutions.

---

## 3. Users / Personas

| Persona | Who they are | Scope | C-02 reach |
|---|---|---|---|
| **Platform Owner** | The SaaS provider operating the platform. | All tenants. | Create user accounts across any institution. Manage lookup tables (UserCategory, Role). View all users across all clients. |
| **Client Director** | The client's top administrator (e.g., trust director, chain owner). | Own client only. | Create user accounts within their client's institutions. Assign roles. Manage lifecycle (suspend, archive). View all users across their client's institutions. |
| **Institution Admin / Principal** | The institution's top in-building administrator. | Own institution only. | Create user accounts within their institution. Assign roles. Manage lifecycle (suspend, archive). View all users at their institution. |
| **Teacher / Staff** | A regular user of the system (teacher, clerk, accountant). | Own account only. | View their own profile. Update their own profile (photo, contact). Cannot create or manage other users. |
| **Student / Parent** | Learners and their guardians. | Own account only. | View their own profile. Update their own profile. Cannot create or manage other users. |

---

## 4. User Journeys

| # | Persona | Journey | Key decisions |
|---|---|---|---|
| **J1** | Client Director | **Onboard a new Teacher.** Create a User record at the institution (email, name, UserCategory = Academic Staff). Assign Role = Teacher. Set lifecycle to Invited. User accepts invitation → Pending → Active. | Decisions 1, 4, 6, 8, 9, 10 |
| **J2** | Institution Admin | **Assign multiple roles to a user.** A teacher is also the HOD of the Science department. Create a second RoleAssignment (User + HOD + scope = "Science Department"). The user now holds Teacher + HOD roles at the same institution. | Decision 6 |
| **J3** | Institution Admin | **Assign a Student ID to a new student.** Create a User record (email, name, UserCategory = Learner). Create a UserIdentifier (type = "student_id", value = "STU-001"). The identifier is unique within the institution. | Decisions 1, 7 |
| **J4** | Client Director | **Suspend a user.** Transition the user's lifecycle from Active → Suspended. A lifecycle event is recorded (state, reason, actor). The user's account is disabled but not deleted. | Decision 8 |
| **J5** | Client Director | **Archive a user.** Transition the user's lifecycle from Active (or Suspended) → Archived. A lifecycle event is recorded. Archived is terminal — the user cannot be reactivated. To "restore" the user, a new account must be created. | Decision 8 |
| **J6** | Institution Admin | **View all users at the institution.** List users filtered by UserCategory (e.g., all Teachers), Role (e.g., all HODs), or lifecycle status (e.g., all Active users). | Decisions 4, 9, 10 |
| **J7** | Teacher / Staff | **Update own profile.** Change photo, phone number, or emergency contact. The user can only update their own UserProfile. | Decision 5 |
| **J8** | Platform Owner | **Manage lookup tables.** Add a new UserCategory ("Visiting Faculty") or a new Role ("Librarian"). These are data inserts, not code changes. | Decisions 9, 10 |
| **J9** | Client Director | **Onboard a user with multiple identifiers.** A teacher also has an Employee ID and an Admission Number (for administrative purposes). Create multiple UserIdentifier records (type = "employee_id" + type = "admission_number") for the same user. | Decision 7 |
| **J10** | Institution Admin | **Reactivate a suspended user.** Transition the user's lifecycle from Suspended → Active. A lifecycle event is recorded. The user's account is re-enabled. | Decision 8 |

---

## 5. Acceptance Criteria

All criteria are testable and trace to a locked decision. Implementation detail (column names, policy text, request shapes) is intentionally omitted.

| # | Criterion | Trace |
|---|---|---|
| **AC-1** | A User belongs to exactly one Client and one Institution. The `client_id` boundary is enforced at two layers: the repository contract (data access from business logic) and a Postgres RLS backstop. A user at School A can never see or edit user data from School B (even if they share the same Client). | Decision 1, D1 |
| **AC-2** | Each User has a UNIQUE email address across the entire platform. No two User records (even across different Clients or Institutions) can share the same email. | Decision 2 |
| **AC-3** | Login with a specific email → access to that email's institution only. No institution picker is shown. To access a different institution, the user logs out and logs back in with the other institution's email. | Decision 3 |
| **AC-4** | All C-02 entities — User, UserProfile, UserCategory, Role, RoleAssignment, UserIdentifier, UserLifecycleEvent — use UUID v4 primary keys. No autoincrement, no C-12-generated codes for these PKs. | Decision 4, D2 |
| **AC-5** | UserProfile is a separate table linked 1:1 to User. Profile fields (photo, date_of_birth, gender, blood_group) are stored in UserProfile, not in the User table. A User can exist without a UserProfile (optional). | Decision 5 |
| **AC-6** | A User can hold multiple RoleAssignments at the same institution (e.g., Teacher + HOD). Each RoleAssignment has a `scope` field defining what the role covers (e.g., "Mathematics Department"). | Decision 6 |
| **AC-7** | RoleAssignment does NOT store `institution_id`. The institution comes from the User record. If a user is at School A, all their role assignments are implicitly at School A. | Decision 6 |
| **AC-8** | UserIdentifier records are unique per (institution, type, value). Two users at the same institution cannot have the same Student ID. Two users at different institutions CAN have the same Student ID. | Decision 7 |
| **AC-9** | UserIdentifier does NOT store `institution_id`. The institution comes from the User record. | Decision 7 |
| **AC-10** | User lifecycle follows the state machine: `Invited → Pending → Active → Suspended → Archived`. Allowed transitions: Invited→Pending, Pending→Active, Active→Suspended, Suspended→Active, Active→Archived, Suspended→Archived. Archived is terminal (no outgoing arcs). | Decision 8 |
| **AC-11** | Every User lifecycle transition records a lifecycle event in `user_lifecycle_event` (state, reason, actor). Events are audited via C-11 (AuditEmitter). | Decision 8 |
| **AC-12** | UserCategory is a lookup table. Adding a new category (e.g., "Visiting Faculty") is a data insert, not a code change. | Decision 9 |
| **AC-13** | Role is a lookup table. Adding a new role (e.g., "Librarian") is a data insert, not a code change. | Decision 10 |
| **AC-14** | User creation requires a valid UserCategory (FK to lookup table). Creating a User without a category or with a non-existent category is rejected. | Decision 9 |
| **AC-15** | RoleAssignment requires a valid Role (FK to lookup table). Creating a RoleAssignment without a role or with a non-existent role is rejected. | Decision 10 |
| **AC-16** | The C-02 module registers via the ModuleManifest Protocol (A5). Routes are registered via `register_routes`. Casbin policies are registered via `register_casbin_policies` (no-op until C-04 is built). | A5 |
| **AC-17** | C-02 repositories inherit TenantAwareRepositoryBase. Queries are automatically filtered by `client_id` from TenantContext. DTOs are returned, not ORM objects. | A6, D1 |
| **AC-18** | C-02 emits audit events via the AuditEmitter Protocol for: user creation, lifecycle transitions, role assignment/removal, identifier creation/deletion. These are synchronous C-11 boundary calls. | C-11 boundary |
| **AC-19** | Configurable enums (UserCategory, Role) are backed by lookup tables — adding a new value is a data insert, no code/deploy. | Decisions 9, 10 |
| **AC-20** | User table has RLS policy on `client_id`. A query without the correct `client_id` filter is blocked by RLS, even if the repository is bypassed. | D1 |

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| **R1** | **Profile duplication across institutions.** A teacher at two schools has two accounts with duplicated name, photo, DOB, gender, blood group. If they update their photo at School A, School B still has the old photo. | Accepted per Decision 1. Multi-institution users are rare (directors, regional managers). For those users, maintaining two profiles is acceptable. Cross-institution identity linking is a future enhancement. |
| **R2** | **Email uniqueness constraint at platform level.** The unique email constraint spans all clients and institutions. If two different clients try to create a user with the same email, the second creation fails. | Accepted per Decision 2. Each client controls their own email namespace (e.g., `teacher@school-a.com` vs `teacher@school-b.com`). Email conflicts across clients are extremely unlikely in practice. |
| **R3** | **No automated user transfer between institutions.** Moving a user from School A to School B requires archiving the old account and creating a new one. Identifiers (Student ID, Employee ID) are lost and must be re-assigned. | Accepted per Decision 8. Automated transfer is a future enhancement. For now, the manual process is acceptable for the rare multi-institution case. |
| **R4** | **RoleAssignment scope is a free-text field.** The `scope` field (e.g., "Mathematics Department") is not validated against any entity. Invalid scopes (e.g., a typo) are silently accepted. | Accepted for Phase 1. Scope validation against OrgUnit or Department is a future enhancement (requires C-01 OrgUnit FK integration). |
| **R5** | **C-02 does not enforce authorization.** Role assignments are stored but not enforced. A user with Role=Teacher can access admin endpoints until C-04 is built. | Accepted per scope decision. C-02 stores the data; C-04 enforces the permissions. Until C-04 is built, authorization is not enforced. This is a known gap, not a bug. |
| **R6** | **Lookup table seed data.** UserCategory and Role tables need seed data (default categories and roles) before any user can be created. If seed data is missing, FK constraints reject user creation. | Seed data will be included in the Alembic migration (same pattern as C-01's `legal_entity_type`, `org_unit_type`, `institution_type_name` lookups). |

---

## 7. Open Questions / Notes

| # | Item | Disposition |
|---|---|---|
| **OQ-1** | Cross-institution identity linking. A future enhancement to link User records across institutions (for directors, regional managers). Would require a lightweight `Person` or `ExternalIdentity` table. | **Deferred.** Not needed for Phase 1. Multi-institution users have separate accounts. Revisit when a concrete requirement emerges. |
| **OQ-2** | UserIdentifier value generation by C-12. The catalog says UserIdentifier values are "generated by C-12." C-02 stores the values; C-12 generates them. The integration point (how C-02 calls C-12 to generate a Student ID) is not yet defined. | **Deferred to C-12.** C-02 accepts identifier values as input. C-12 integration is a future enhancement. |
| **OQ-3** | RoleAssignment scope validation against OrgUnit. The `scope` field is free-text in Phase 1. Future enhancement: validate scope against C-01 OrgUnit hierarchy (e.g., "Mathematics Department" must exist as an OrgUnit). | **Deferred.** Requires C-01 OrgUnit FK integration. |
| **OQ-4** | User lifecycle approval flow. C-01 has an Approval mechanism (Q3). Should C-02 lifecycle transitions (e.g., Invited → Active) also require approval? | **Deferred.** Phase 1 lifecycle transitions are direct (no approval flow). Revisit when C-04 authorization is built. |
| **OQ-5** | UUID v7 (time-ordered) revisit. C-01 uses UUID v4. C-02 follows the same pattern. UUID v7 is a drop-in candidate if pagination/indexing benchmarks show value. | **Deferred.** Same as C-01 OQ-5. |
| **OQ-6** | User soft-delete vs hard-delete. Phase 1 uses archive-only (soft-delete). No hard-delete path. Should there be a GDPR-compliant hard-delete mechanism? | **Deferred.** Phase 1 is archive-only. GDPR compliance is a future concern. |

---

## 8. Traceability Matrix (compact)

| PRD section | Primary anchors |
|---|---|
| §1 Problem | platform-capabilities-v3 §C-02; architecture-v1 §5, §6, §6.1 |
| §2.1 In scope | Decisions 1–11; A3, A5, A6 |
| §2.2 Out of scope | C-03, C-04, C-05, C-06, C-09, C-11, C-12 |
| §2.3 Phase 1 non-goals | Decisions 1, 3, 8 |
| §3 Personas | Decisions 1, 4, 6, 9, 10 |
| §4 Journeys J1–J10 | Decisions 1–10 |
| §5 Acceptance criteria AC-1…AC-20 | Decisions 1–11; A3, A5, A6; D1, D2; C-11 boundary |
| §6 Risks | Decisions 1, 2, 6, 7, 8; C-04 boundary |
| §7 Open questions | C-06 boundary; C-12 boundary; C-04 boundary |

---

## 9. Decision Log (from grill-me session)

| # | Decision | Lock |
|---|---|---|
| 1 | Person model | No `Person` table — `User` per institution |
| 2 | Email uniqueness | Each `User` has a UNIQUE email |
| 3 | Login flow | Login with specific email → access specific institution |
| 4 | User table | `id`, `client_id`, `institution_id`, `email`, `name`, `user_category_id`, `lifecycle_status` |
| 5 | UserProfile | Separate table — `photo`, `date_of_birth`, `gender`, `blood_group` |
| 6 | RoleAssignment | `user_id` + `role_id` + `scope` (institution from User) |
| 7 | UserIdentifier | `user_id` + `type` + `value` (institution from User) |
| 8 | UserLifecycle | `Invited → Pending → Active → Suspended → Archived` (Archived terminal) |
| 9 | UserCategory | Lookup table (configurable) |
| 10 | Role | Lookup table (configurable) |
| 11 | Scope | Full C-02 in Phase 1 |

---

## 10. Entities Summary

| Entity | Table | Key Fields | Relationships |
|---|---|---|---|
| User | `user` | `id`, `client_id`, `institution_id`, `email`, `name`, `user_category_id`, `lifecycle_status` | FK → UserCategory. Has many: UserProfile, RoleAssignment, UserIdentifier, UserLifecycleEvent |
| UserProfile | `user_profile` | `id`, `user_id`, `photo`, `date_of_birth`, `gender`, `blood_group` | FK → User (1:1) |
| UserCategory | `user_category` | `id`, `name` | Lookup table. Referenced by User.user_category_id |
| Role | `role` | `id`, `name` | Lookup table. Referenced by RoleAssignment.role_id |
| RoleAssignment | `role_assignment` | `id`, `user_id`, `role_id`, `scope` | FK → User, Role |
| UserIdentifier | `user_identifier` | `id`, `user_id`, `type`, `value` | FK → User |
| UserLifecycleEvent | `user_lifecycle_event` | `id`, `user_id`, `state`, `reason`, `actor` | FK → User |

---

> End of PRD — C-02 Identity & User Management. Next SDD phase: impact classification → proposal/spec/design/tasks.
