# PRD — C-04 Authorization

> **Capability:** C-04 Authorization
> **Capability layer / phase:** Kernel · Critical · Phase 1
> **Status:** Draft for impact classification → proposal/spec/design/tasks
> **Last updated:** 2026-07-13
> **Decisional source of truth:** Grill-me session (33 locked decisions, 2026-07-13)
> **Companion docs:** `docs/platform-capabilities/platform-capabilities-v3.md` §C-04; `docs/architecture/adr-platform-software-architecture.md` (A2, A5, A6); `docs/architecture/adr-platform-tech-stack.md` (AuthZ row — Casbin); `docs/prd/c-01-tenant-institution.md` (D11 permission matrix); `docs/prd/c-02-identity-user-management.md` (Role/RoleAssignment tables); `docs/prd/c-03-authentication.md` (D7 — TenantContext.roles from middleware)
> **Scope note:** This is a **product** requirements document. Implementation detail (Casbin policy format, dependency wiring, exact seed SQL) belongs in the spec/design phase. Decisions are referenced by their grill-me number (e.g., "per D1") rather than re-specified here.

---

## 1. Problem

Every business module in the School ERP — Attendance, Fees, Homework, Exams, Timetable — needs to know **what a user can do**. A Teacher should mark attendance but not create institutions. A Student should submit homework but not suspend other users. A Parent should view their child's grades but not change them. Without a centralized authorization capability, each module would implement its own permission checks — leading to fragmented access control, inconsistent enforcement, and security gaps.

C-04 provides the **single authorization gateway** for the entire platform. It answers: given an authenticated user (C-03), what operations are they allowed to perform on what resources, within what organizational scope? C-04 sits between C-03 (which knows who the user is) and every business module endpoint that needs to gate access.

The key architectural decision that shaped this PRD: **Casbin owns the enforcement engine; C-04 owns the permission catalog and the role-to-permission mapping.** C-02's `Role` table (Teacher, HOD, Principal, Student, Parent, Staff, Admin) defines what a user IS — identity labels. C-04's new `permission` and `role_permission` tables define what each role can DO — authorization rules. This clean separation (D1) means C-02 stays untouched while C-04 builds the permission layer on top.

C-04 also **retrofits** all existing C-01 and C-02 endpoints with authorization checks (D16). Every endpoint that creates, reads, updates, or deletes resources must declare its required permission. This is done via a single FastAPI dependency `require_permission(resource, action, ...)` that each endpoint opts into (D5).

---

## 2. Goals & Non-goals

### 2.1 In scope — C-04 owns

| Entity / concern | Per | Notes |
|---|---|---|
| **Permission catalog** | D8, D18, D30 | `permission` table with 26 Phase 1 permissions in `resource.action` format (e.g., `client.create`, `user.read`). Global lookup table — no RLS, same for all clients. |
| **Role-permission mapping** | D8, D15, D26 | `role_permission` table mapping C-02's `role` rows to `permission` rows. FK to C-02's `role` table. ~40 seed rows defining what each of the 7 C-02 roles can do. All C-02 permissions use `institution` Casbin scope. |
| **Casbin model + enforcer** | D4, D10, D25 | Central `casbin_model.conf` moved from C-01 to `kernel/authz/`. App factory creates the enforcer singleton and calls each module's `register_casbin_policies(enforcer)` hook in dependency order. Model unchanged from C-01 (already supports RBAC role hierarchy + ABAC scope checks). |
| **`require_permission` dependency** | D5, D7, D12, D19, D22, D31 | FastAPI dependency that each endpoint opts into. Reads `TenantContext.roles` (D13), builds Casbin subject/object, calls `enforcer.enforce()`. Two-step enforcement: Casbin for role+scope; app-level for ownership (D12). Accepts explicit object attributes (`client_id`, `institution_id`, `owner_id`) from the calling endpoint. |
| **Retrofitted C-01 endpoints (~15)** | D16, D20 | All C-01 endpoints gain `Depends(require_permission(...))`. MODIFIED delta spec for `tenant-institution`. |
| **Retrofitted C-02 endpoints (~12)** | D16, D20 | All C-02 endpoints gain `Depends(require_permission(...))`. MODIFIED delta spec for `identity-user-management`. |
| **`platform_owner` role** | D27, D28 | A new row in C-02's `role` table (added by C-04 migration). Assigned to the platform owner user via `role_assignment`. C-04's `role_permission` does NOT map it — C-01's existing D11 Casbin policies grant `*.*` at `any` scope. |

#### 2.1.1 Phase 1 permissions — 26 total

| Resource | Actions | Count |
|---|---|---|
| `client` | `read`, `update`, `transfer_ownership`, `transition_lifecycle` | 4 |
| `institution` | `read`, `create`, `update`, `transition_lifecycle` | 4 |
| `org_unit` | `read`, `create`, `update`, `delete`, `move` | 5 |
| `institution_type` | `read` | 1 |
| `user` | `read`, `create`, `update`, `suspend` | 4 |
| `user_profile` | `read`, `update` | 2 |
| `role_assignment` | `read`, `create`, `delete` | 3 |
| `user_identifier` | `read`, `create`, `delete` | 3 |

Note: `client.create` and `client.delete` are **not** in the C-04 permission catalog — these are platform-gated operations handled exclusively by C-01's existing D11 Casbin policies (`platform_owner` at `any` scope).

#### 2.1.2 Phase 1 role-to-permission mapping (D15)

| C-02 Role | C-01 Permissions | C-02 Permissions | Scope |
|---|---|---|---|
| **Admin** | `institution.read`, `org_unit.*`, `institution_type.read` | `user.*`, `user_profile.read`, `role_assignment.*`, `user_identifier.*` | institution |
| **Principal** | `institution.read`, `institution.update`, `org_unit.*`, `institution_type.read` | `user.read`, `role_assignment.read`, `user_identifier.read` | institution |
| **HOD** | `org_unit.read`, `org_unit.update`, `institution_type.read` | `user.read`, `role_assignment.read` | institution |
| **Teacher** | — | `user.read`, `user.update` (own profile only via ownership check D22) | institution |
| **Staff** | — | `user.read`, `user.update` (own profile only via ownership check D22) | institution |
| **Student** | — | `user.read` (own profile only via ownership check D22) | institution |
| **Parent** | — | `user.read` (own profile only via ownership check D22), `user_identifier.read` | institution |

Platform roles (`platform_owner`, `client_director`, `institution_admin`, `cross_institution`) are handled by C-01's existing D11 Casbin policies — they are Casbin-only labels, NOT in C-02's `role` table, and NOT in C-04's `role_permission` mapping (D27).

### 2.2 Out of scope — owned by other capabilities

| Concern | Owned by | Notes |
|---|---|---|
| User identity and domain fields (name, category, profiles) | C-02 | C-04 tells you what you can do; C-02 tells you who you are. |
| Role lookup table (C-02's `role`) | C-02 | C-04 reads C-02's `role` table via FK (correct tier order: Level 3 → Level 2). C-02 remains the single source of truth for role labels. |
| Authentication (login, JWT, sessions) | C-03 | C-04 assumes the user is authenticated. It reads `TenantContext.roles` set by C-03's middleware (D7). |
| Audit framework | C-11 | Access denials (403 from `require_permission`) are recorded via the existing `AuditEmitter` Protocol, not a C-04-specific audit table. |
| `TemporaryRole` (roles with expiry) | Phase 2 | Deferred. C-04 models the table then but not now (D21). |
| `Policy` ABAC rules | Phase 3 | Deferred. The Casbin model is ABAC-ready but Phase 1 uses RBAC only for permission resolution (D21). |

### 2.3 Explicit non-goals for Phase 1

- **No permission CRUD API** — permissions are seeded in the migration and loaded at startup. No `GET/POST/PUT/DELETE /api/v1/permissions` endpoints in Phase 1 (D23).
- **No configurable roles UI** — Phase 2 delivers an admin UI for editing role-to-permission mappings. Phase 1 uses seed data.
- **No runtime policy reload** — `reload_policies()` endpoint deferred to Phase 2. Phase 1 requires an app restart to pick up permission changes (D11).
- **No fine-grained scopes** — Phase 1 enforces only `institution` scope in Casbin. Phase 2 adds OrgUnit, Grade, Class, Subject scopes (requires C-05 Academic Structure, D6).
- **No ABAC policy engine** — the Casbin model supports ABAC but Phase 1 does not define ABAC policies. Ownership checks are handled at the app level, not in Casbin (D12).
- **No separate Permission or RolePermission repositories** — ORM models exist for migration and startup loader only. Direct SQL is used to read `role_permission` at startup (D23).
- **No `TemporaryRole` or `Policy` tables** — deferred to Phase 2 (TemporaryRole) and Phase 3 (Policy), per D21.

---

## 3. Users / Personas

| Persona | Who they are | Scope | C-04 reach |
|---|---|---|---|
| **Platform Owner** | The SaaS provider operating the platform. | All tenants — `any` scope. | All C-01 and C-02 operations via `*.*` (C-01's D11 policies). View all permissions. |
| **Client Director** | The client's top administrator. | Own client — `tenant` scope. | Client read/update, institution CRUD, OrgUnit management within own client. Cannot create/suspend/delete the client itself. |
| **Institution Admin** | The institution's top in-building administrator. | Own institution — `institution` scope. | Institution read/update, OrgUnit management, full user management (create, update, suspend, role assignment, identifiers) at own institution. |
| **Principal** | School head. | Own institution. | Institution read/update, OrgUnit management, read-only user/role/identifier access at own institution. |
| **HOD** | Department head. | Own institution. | OrgUnit read/update within own institution. Read-only user/role access. |
| **Teacher** | Classroom practitioner. | Own institution (own profile). | Read/update own user profile only. No C-01 access. |
| **Staff** | Administrative staff. | Own institution (own profile). | Read/update own user profile only. No C-01 access. |
| **Student** | Learner. | Own institution (own profile). | Read own user profile only. No C-01 access. |
| **Parent** | Guardian. | Own institution (own profile + related students). | Read own user profile and linked student identifiers. No C-01 access. |

---

## 4. Functional Requirements (User Stories & Acceptance Criteria)

### 4.1 Permission catalog

**AC-1 Enumerate all Phase 1 permissions.** The `permission` table must contain exactly 26 rows covering C-01 (14) and C-02 (12) resources with the actions listed in §2.1.1. Each row has a unique `name`, a `description`, a `resource` column, and an `action` column (D30).

**AC-2 Role-permission mapping is seeded.** The `role_permission` table must map each of the 7 C-02 roles to their allowed permissions per §2.1.2. A Teacher must have `user.read` and `user.update` but NOT `user.create` or `user.suspend`.

**AC-3 Permissions are isolated from tenants.** `permission` and `role_permission` tables must have no RLS policies — they are global data shared across all clients (D8).

### 4.2 Authorization enforcement

**AC-4 Any protected endpoint requires a permission.** Every C-01 and C-02 endpoint must declare `Depends(require_permission(...))` with the appropriate resource, action, and object attributes. An unpermissioned request must return HTTP 403 with a descriptive detail message.

**AC-5 Role-based access works correctly.** An Institution Admin with roles `["Admin"]` must be able to call `POST /api/v1/users` (`user.create`). A Teacher with roles `["Teacher"]` must receive 403 when calling the same endpoint.

**AC-6 Platform Owner bypasses all permission checks.** A user with `roles = ["platform_owner"]` must be able to call any endpoint. C-01's D11 policies grant `*.*` at `any` scope.

**AC-7 Scope enforcement works at the Casbin level.** An Institution Admin at School A cannot create an institution at School B (cross-institution). The Casbin check must verify `sub.institution_id == obj.institution_id` for `institution`-scoped permissions (D26).

**AC-8 Cross-tenant access is blocked.** A Client Director at Client A cannot read institutions belonging to Client B. The Casbin check must verify `sub.client_id == obj.client_id` for `tenant`-scoped permissions.

### 4.3 Ownership enforcement (app-level)

**AC-9 Users can only access their own profiles.** A Teacher calling `GET /api/v1/users/{id}` or `PATCH /api/v1/users/{id}` must receive 403 if `{id}` is not their own user ID — unless they hold an admin-level role with `institution` scope (D22).

**AC-10 Admin roles bypass ownership.** An Institution Admin calling `GET /api/v1/users/{id}` where `{id}` is a different user but within the same institution must receive 200 — the Casbin check passes (admin has `institution` scope), and the ownership check is bypassed because the user's scope covers the institution.

### 4.4 Casbin enforcer lifecycle

**AC-11 The Casbin enforcer is a singleton created at app startup.** The app factory must create exactly one Casbin enforcer from `kernel/authz/casbin_model.conf`, register all module policies via the `register_casbin_policies` hook in dependency order (C-01 → C-02 → C-03 → C-04), and make it available via `get_enforcer()` (D10).

**AC-12 C-04's policies are loaded from the database at startup.** C-04's `on_startup` hook must read all `role_permission` rows, build an in-memory permission map, and C-04's `register_casbin_policies` hook must add the corresponding Casbin policies and role groupings (D24).

**AC-13 Policy evaluation is in-memory.** At request time, `require_permission` must call `enforcer.enforce()` which runs purely in-memory — no database hit (D11).

### 4.5 Existing C-01/C-02 retrofit

**AC-14 All C-01 endpoints are retrofitted with authorization.** Every endpoint in `backend/business/tenant_institution/routes/` must include `Depends(require_permission(...))`. Existing C-01 tests must continue to pass (seed permission data or override dependency).

**AC-15 All C-02 endpoints are retrofitted with authorization.** Every endpoint in `backend/kernel/user/routes/` must include `Depends(require_permission(...))`. Existing C-02 tests must continue to pass.

**AC-16 C-01's `build_enforcer()` is removed.** C-01 no longer builds its own Casbin enforcer. Its `register_casbin_policies(enforcer)` hook receives the central enforcer from C-04 (D14). Any test that used `build_enforcer()` must use `get_enforcer()` instead.

**AC-17 C-01's Casbin model is moved to C-04.** The file `business/tenant_institution/casbin_model.conf` must be moved to `kernel/authz/casbin_model.conf`. All references must be updated (D14).

### 4.6 `platform_owner` role

**AC-18 The `platform_owner` role exists in C-02's role table.** C-04's migration must insert a `platform_owner` row into C-02's `role` table. The bootstrap CLI (C-03) assigns this role to the platform owner user via `role_assignment` (D28).

**AC-19 `platform_owner` is not mapped in C-04's `role_permission` table.** The platform owner receives `*.*` access via C-01's existing D11 Casbin policies, not via the `role_permission` mapping (D27).

### 4.7 Import and dependency integrity

**AC-20 C-04 respects the kernel dependency law.** `kernel/authz/` must only import from `kernel/` packages and standard library / third-party packages. It must not import from `business/` or `shared/` (D32, A3).

**AC-21 The dependency graph remains acyclic.** C-04 (Level 3) may import from C-02 (Level 2) and C-01a (Level 1). Lower levels must not import from C-04. Import-linter must keep all existing contracts (A4, D32).

### 4.8 Testing

**AC-22 Authorization rules are tested with the real Casbin enforcer.** C-04 tests must build a Casbin enforcer with the real model and real policies, then assert `enforcer.enforce(subject, object, action)` returns true or false for each role-permission-scope combination (D17). The C-01 `test_casbin_permissions.py` pattern is the reference.

**AC-23 The `require_permission` dependency is tested in isolation.** Unit tests must verify that the dependency raises 403 for unauthorized roles and returns successfully for authorized roles, using a TenantContext with known role labels.

**AC-24 C-01/C-02 retrofit tests continue to pass.** Existing C-01 and C-02 tests must continue to pass after retrofitting. Test fixtures must provide sufficient seed data (role + permission + role_permission rows) or override the dependency for tests that don't need to exercise authorization.

---

## 5. User Journeys

### J1: Institution Admin creates a new user (happy path)

1. Institution Admin logs in → JWT with `roles = ["Admin"]`.
2. Middleware resolves TenantContext with `client_id`, `institution_id`, `roles`.
3. Admin calls `POST /api/v1/users` with `{email, name, user_category_id, institution_id}`.
4. `require_permission("user", "create", client_id=..., institution_id=...)` runs.
5. Casbin checks: does role `Admin` have permission `user.create` at `institution` scope? → Yes (per D15).
6. C-02 service creates the user + propagates to Supabase Auth.
7. Returns 201 Created.

### J2: Teacher tries to create a user (denied)

1. Teacher logs in → JWT with `roles = ["Teacher"]`.
2. Teacher calls `POST /api/v1/users`.
3. `require_permission("user", "create", ...)` runs.
4. Casbin checks: does role `Teacher` have permission `user.create`? → No (per D15: Teacher only has `user.read`, `user.update`).
5. Returns 403 Forbidden: "Permission denied: user.create requires role with institution scope."

### J3: Teacher views their own profile (ownership check)

1. Teacher (user_id = UUID-A) calls `GET /api/v1/users/UUID-A`.
2. `require_permission("user", "read", client_id=..., institution_id=..., owner_id=UUID-A)` runs.
3. Casbin checks: does Teacher have `user.read` at `institution` scope? → Yes.
4. Ownership check: `owner_id == ctx.user_id` → Yes.
5. Returns 200 OK with the user profile.

### J4: Teacher tries to view another teacher's profile (ownership denied)

1. Teacher (user_id = UUID-A) calls `GET /api/v1/users/UUID-B` (different user).
2. `require_permission("user", "read", client_id=..., institution_id=..., owner_id=UUID-B)` runs.
3. Casbin checks: does Teacher have `user.read` at `institution` scope? → Yes.
4. Ownership check: `owner_id (UUID-B) != ctx.user_id (UUID-A)` → Fails.
5. Check admin bypass: is Teacher's scope `institution` via Casbin? → Teacher only has institution scope for profile read, but ownership blocks cross-user access.
6. Returns 403 Forbidden: "You can only access your own profile."

### J5: Institution Admin views any user at their institution (admin bypass)

1. Institution Admin (user_id = UUID-X, roles=["Admin"]) calls `GET /api/v1/users/UUID-B`.
2. Casbin checks: does Admin have `user.read` at `institution` scope? → Yes.
3. Ownership check: `owner_id (UUID-B) != ctx.user_id (UUID-X)` → Fails.
4. Admin bypass: Casbin scope check confirms Admin has `institution` scope — Admin can read any user in their institution.
5. Returns 200 OK.

### J6: Cross-institution access blocked

1. Institution Admin at School A calls `POST /api/v1/institutions` with `client_id=SchoolA, institution_id=SchoolB` (attempts to create an institution at School B).
2. `require_permission("institution", "create", client_id=SchoolA, institution_id=SchoolB)` runs.
3. Casbin checks: `sub.institution_id (SchoolA) == obj.institution_id (SchoolB)` → Fails.
4. Returns 403 Forbidden.

### J7: Cross-tenant access blocked

1. Client Director at Client A calls `GET /api/v1/clients` and tries to view Client B.
2. Casbin checks: `sub.client_id (ClientA) != obj.client_id (ClientB)` → Fails for `tenant` scope.
3. Returns 403 Forbidden.

### J8: Platform Owner accesses anything

1. Platform Owner (roles=["platform_owner"]) calls any endpoint.
2. Casbin checks: C-01's D11 policy grants `*.*` at `any` scope → passes.
3. No ownership check needed. No scope restriction.
4. Operation proceeds.

### J9: Permission catalog query for future UI

1. In Phase 2, an admin UI needs to show "what permissions does Teacher have?"
2. Query: `SELECT p.name FROM permission p JOIN role_permission rp ON p.id = rp.permission_id JOIN role r ON r.id = rp.role_id WHERE r.name = 'Teacher'`
3. Returns: `["user.read", "user.update"]`.
4. In Phase 1, this query is available but no API endpoint exposes it — used internally by tests and validation.

### J10: Casbin startup sequence

1. App starts.
2. Alembic migration 004 creates `permission`, `role_permission` tables and seeds data.
3. C-04's `on_startup` runs: reads `role_permission` from DB into an in-memory dict.
4. App factory creates Casbin enforcer from `kernel/authz/casbin_model.conf`.
5. Factory calls `register_casbin_policies(enforcer)` in order: C-01 adds D11 matrix → C-02 (empty) → C-03 (empty) → C-04 adds permission-based policies from the in-memory dict.
6. Enforcer ready. `get_enforcer()` returns the singleton.

---

## 6. Key Rules

1. **Authorization is centralized** — no module implements its own permission system. All access control goes through `require_permission`.
2. **Permissions are evaluated dynamically** — Casbin combines the user's roles (from TenantContext), the target resource/action, and the scope to make a decision.
3. **Cross-institution access must be explicitly granted** — the Casbin `institution` scope check ensures `sub.institution_id == obj.institution_id`. Cross-institution operations (like the cross-institution READ-only oversight role) are explicitly configured in C-01's D11 policies.
4. **Cross-client access is never permitted** — the Casbin `tenant` scope check ensures `sub.client_id == obj.client_id`. Platform owner operations use `any` scope to bypass this.
5. **Ownership is always checked** — for C-02 profile endpoints, ownership is verified at the app level in addition to Casbin's role+scope check. Admin roles with `institution` scope bypass ownership.
6. **Permissions are static in Phase 1** — changing what a role can do requires a migration + app restart. Phase 2 adds the `reload_policies()` endpoint and admin UI for runtime changes.

---

## 7. Acceptance Criteria (Consolidated Mapping)

| AC | Title | Validates | Journey |
|---|---|---|---|
| AC-1 | 26 permissions seeded in `permission` table | D8, D18, D30 | — |
| AC-2 | Role-to-permission mapping seeded (~40 rows) | D15, D26 | — |
| AC-3 | Permission tables have no RLS (global data) | D8 | — |
| AC-4 | All protected endpoints have `require_permission` | D5, D16, D31 | J1–J8 |
| AC-5 | Role-based access enforced (Casbin) | D5, D15 | J1, J2 |
| AC-6 | Platform Owner bypasses all checks | D27, D28 | J8 |
| AC-7 | Institution-level scope enforced by Casbin | D6, D26 | J6 |
| AC-8 | Cross-tenant access blocked by Casbin | D6, D26 | J7 |
| AC-9 | Ownership check blocks cross-user access | D12, D22 | J4 |
| AC-10 | Admin roles bypass ownership | D22 | J5 |
| AC-11 | Casbin enforcer is a singleton created at startup | D10, D29 | J10 |
| AC-12 | C-04 policies loaded from DB at startup | D11, D24 | J10 |
| AC-13 | Policy evaluation is in-memory at runtime | D11 | J1–J8 |
| AC-14 | All C-01 endpoints retrofitted with `require_permission` | D14, D16 | — |
| AC-15 | All C-02 endpoints retrofitted with `require_permission` | D16 | — |
| AC-16 | C-01's `build_enforcer()` removed | D14 | — |
| AC-17 | Casbin model moved to `kernel/authz/` | D4, D14 | — |
| AC-18 | `platform_owner` row in C-02's `role` table | D28 | J8 |
| AC-19 | `platform_owner` NOT in C-04's `role_permission` | D27 | J8 |
| AC-20 | C-04 respects kernel dependency law (A3) | D9, D32 | — |
| AC-21 | Dependency graph remains acyclic (A4) | D32 | — |
| AC-22 | Authorization rules tested with real Casbin enforcer | D17 | — |
| AC-23 | `require_permission` dependency tested in isolation | D17 | J2, J4 |
| AC-24 | C-01/C-02 retrofit tests continue to pass | D16, D20 | — |

---

## 8. Dependencies

| Capability | Type | Rationale |
|---|---|---|
| C-01a (Tenant Identity Infrastructure) | Infrastructure | `TenantContext`, subdomain+JWT middleware (C-04 reads `client_id`, `institution_id`, `roles` from context). C-01's D11 Casbin policies define the platform-level role matrix. |
| C-02 (Identity & User Management) | Data + FK | C-02's `role` table is the source of truth for role labels. C-04's `role_permission` has an FK to `role.id`. C-02's `role_assignment` is read by C-03 middleware to populate `TenantContext.roles`. |
| C-03 (Authentication) | Runtime | C-03's middleware (D7) populates `TenantContext.roles` from `role_assignment`. `require_permission` reads this list. Without C-03, there's no authenticated user to authorize. |
| C-11 (Audit Framework) | Boundary | Access denials are emitted via the `AuditEmitter` Protocol (same pattern as C-01, C-02, C-03). |
| C-05 (Academic Structure) | Future | Phase 2 fine-grained scope (OrgUnit, Grade, Class) requires C-05 to provide the scope entities. Not a Phase 1 dependency. |

---

## 9. Open Questions & Future Evolution

| # | Question | Status |
|---|---|---|
| — | All 33 decisions locked in grill-me session | ✅ Final |
| — | Phase 2: `TemporaryRole` table and expiry logic | Deferred (D21) |
| — | Phase 2: Permission CRUD API and admin UI | Deferred (D23) |
| — | Phase 2: `reload_policies()` for runtime permission changes | Deferred (D11) |
| — | Phase 2: Fine-grained scopes (OrgUnit, Grade, Class) — requires C-05 | Deferred (D6) |
| — | Phase 3: ABAC Policy engine (ownership checks in Casbin instead of app-level) | Deferred (D21) |
