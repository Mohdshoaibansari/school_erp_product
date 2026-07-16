## Purpose

C-04 Authorization provides the centralized access control layer for the School ERP platform. It owns the `permission` catalog, `role_permission` mapping, the Casbin enforcement engine, the `require_permission` FastAPI dependency, and ownership enforcement. C-04 answers: given an authenticated user (C-03), what operations are they allowed to perform on what resources, within what organizational scope? This spec is the behavioral source of truth derived from the grill-me session (D1–D33) and PRD `docs/prd/c-04-authorization.md` (AC-1..AC-24).

## Requirements

### Requirement: Permission Catalog

The system SHALL maintain a `permission` table cataloging all Phase 1 permissions in `resource.action` format (D2, D30). The table SHALL contain exactly 26 rows covering C-01 (14) and C-02 (12) resources with the actions listed below. Each row SHALL have a unique `name`, a `description`, a `resource` column, and an `action` column. The table SHALL have no RLS policies — it is global data shared across all clients (D8).

C-01 permissions: `client.read`, `client.update`, `client.transfer_ownership`, `client.transition_lifecycle`, `institution.read`, `institution.create`, `institution.update`, `institution.transition_lifecycle`, `org_unit.read`, `org_unit.create`, `org_unit.update`, `org_unit.delete`, `org_unit.move`, `institution_type.read`.

C-02 permissions: `user.read`, `user.create`, `user.update`, `user.suspend`, `user_profile.read`, `user_profile.update`, `role_assignment.read`, `role_assignment.create`, `role_assignment.delete`, `user_identifier.read`, `user_identifier.create`, `user_identifier.delete`.

Note: `client.create` and `client.delete` are NOT in the C-04 permission catalog — these are platform-gated operations handled exclusively by C-01's existing D11 Casbin policies.

Trace: D8, D18, D30, D3, AC-1, AC-3.

#### Scenario: All 26 permissions are seeded in the migration
- **WHEN** Alembic migration 004 is applied
- **THEN** the `permission` table contains exactly 26 rows with the names listed above, each with a unique `name`, a non-empty `description`, and matching `resource` and `action` columns

#### Scenario: Permission names are unique
- **WHEN** an attempt is made to insert a duplicate `name` into the `permission` table
- **THEN** the database rejects the insert with a unique constraint violation

#### Scenario: Permission table has no RLS
- **WHEN** any authenticated user queries the `permission` table directly (not through an API — through any SQL path)
- **THEN** all 26 rows are visible (global data, no tenant filtering)

### Requirement: Role-Permission Mapping

The system SHALL maintain a `role_permission` table mapping C-02's `role` rows to `permission` rows via FK (D8). The table SHALL be seeded with the role-to-permission mapping defined in the PRD §2.1.2. A unique constraint on `(role_id, permission_id)` SHALL prevent duplicate mappings. The table SHALL have no RLS — global data (D8).

The mapping per C-02 role:
- **Admin**: `institution.read`, `org_unit.*` (all 5), `institution_type.read`, `user.*` (all 4), `user_profile.read`, `role_assignment.*` (all 3), `user_identifier.*` (all 3). Scope: `institution`.
- **Principal**: `institution.read`, `institution.update`, `org_unit.*` (all 5), `institution_type.read`, `user.read`, `role_assignment.read`, `user_identifier.read`. Scope: `institution`.
- **HOD**: `org_unit.read`, `org_unit.update`, `institution_type.read`, `user.read`, `role_assignment.read`. Scope: `institution`.
- **Teacher**: `user.read`, `user.update`. Scope: `institution` (ownership check restricts to own profile).
- **Staff**: `user.read`, `user.update`. Scope: `institution` (ownership check restricts to own profile).
- **Student**: `user.read`. Scope: `institution` (ownership check restricts to own profile).
- **Parent**: `user.read`, `user_identifier.read`. Scope: `institution` (ownership check restricts to own profile).

Trace: D8, D15, D26, AC-2, AC-3.

#### Scenario: Role-permission mapping is seeded correctly
- **WHEN** Alembic migration 004 is applied
- **THEN** the `role_permission` table contains mappings for all 7 C-02 roles, each mapped to their permitted permissions as listed above

#### Scenario: Teacher does NOT have user.create permission
- **WHEN** querying `role_permission` for the Teacher role
- **THEN** the result set does NOT include `user.create` or `user.suspend`

#### Scenario: Duplicate mapping is rejected
- **WHEN** an attempt is made to insert a duplicate `(role_id, permission_id)` pair
- **THEN** the database rejects the insert with a unique constraint violation

### Requirement: Casbin Enforcer Singleton

The system SHALL create exactly one Casbin enforcer at app startup from the model at `kernel/authz/casbin_model.conf` (D4, D10, D25). The app factory SHALL iterate the registered module manifests in dependency order (C-01 → C-02 → C-03 → C-04) and call each manifest's `register_casbin_policies(enforcer)` hook (A5, D29). The enforcer SHALL be available as a FastAPI dependency via `get_enforcer()` (D10).

Trace: D4, D10, D25, D29, AC-11.

#### Scenario: Enforcer is a singleton
- **WHEN** `get_enforcer()` is called twice within the same application lifecycle
- **THEN** the same enforcer instance is returned both times (singleton)

#### Scenario: All module policies are registered in dependency order
- **WHEN** the app starts
- **THEN** C-01's D11 policies are registered first, then C-02 (empty hook), then C-03 (empty hook), then C-04's permission-based policies last

#### Scenario: Enforcer uses the centralized model
- **WHEN** the enforcer is created at startup
- **THEN** it uses the Casbin model file at `kernel/authz/casbin_model.conf`

### Requirement: C-04 Policy Registration

C-04's `on_startup` hook SHALL read all `role_permission` rows from the database into an in-memory mapping (D24). C-04's `register_casbin_policies(enforcer)` hook SHALL iterate the in-memory mapping and add Casbin policies (`enforcer.add_policy(role, resource, action, scope)`) and role groupings (`enforcer.add_grouping_policy(user_role, casbin_label)`). All C-02 permissions SHALL use `institution` Casbin scope (D26).

At request time, `enforcer.enforce()` SHALL run purely in-memory — no database hit (D11).

Trace: D11, D24, D26, D29, AC-12, AC-13.

#### Scenario: C-04 policies loaded from DB at startup
- **WHEN** the app starts and C-04's `on_startup` completes
- **THEN** the in-memory permission map contains all role-to-permission mappings from the `role_permission` table

#### Scenario: Policy evaluation is in-memory at runtime
- **WHEN** `require_permission` calls `enforcer.enforce(subject, object, action)` at request time
- **THEN** the enforcement runs purely in-memory (no SQL query to `role_permission` or `permission`)

### Requirement: `require_permission` FastAPI Dependency

The system SHALL provide a `require_permission(resource, action, client_id, institution_id, owner_id)` FastAPI dependency (D5). The dependency SHALL read `TenantContext.roles` from the contextvar (D13), build a Casbin subject (`{role, client_id, institution_id}`) and object (`{name: resource, client_id, institution_id}`), call `enforcer.enforce(subject, object, action)`, and raise HTTP 403 with a descriptive detail message on denial (D5, D7).

Object attributes (`client_id`, `institution_id`) SHALL be passed explicitly by the calling endpoint (D7, D19). Create endpoints may pass optimistic values (the resource doesn't exist yet — scope is enforced at DB layer by RLS). List endpoints may pass only the client scope (no institution_id).

Trace: D5, D7, D13, D19, AC-4, AC-5.

#### Scenario: Authorized role passes the check
- **WHEN** an Admin (roles=["Admin"], institution_id=X) calls `require_permission("user", "create", client_id=Y, institution_id=X)`
- **THEN** Casbin enforces the check, the role `Admin` has `user.create` at `institution` scope, `sub.institution_id == obj.institution_id`, and the dependency returns silently (no exception)

#### Scenario: Unauthorized role receives 403
- **WHEN** a Teacher (roles=["Teacher"]) calls `require_permission("user", "create", ...)`
- **THEN** Casbin enforces the check, the role `Teacher` does NOT have `user.create`, and the dependency raises HTTP 403 "Permission denied: user.create requires role with institution scope"

#### Scenario: Cross-institution access returns 403
- **WHEN** an Admin (roles=["Admin"], institution_id=SchoolA) calls `require_permission("institution", "read", client_id=ClientX, institution_id=SchoolB)`
- **THEN** Casbin checks `sub.institution_id (SchoolA) == obj.institution_id (SchoolB)` → fails, and the dependency raises HTTP 403

#### Scenario: Cross-tenant access returns 403
- **WHEN** a Client Director (roles=["client_director"], client_id=ClientA) calls `require_permission("institution", "read", client_id=ClientB)`
- **THEN** Casbin checks `sub.client_id (ClientA) == obj.client_id (ClientB)` → fails at `tenant` scope, and the dependency raises HTTP 403

### Requirement: Platform Owner Bypass

A user with `roles = ["platform_owner"]` SHALL be able to call any endpoint without restriction (D28). C-01's D11 Casbin policies SHALL grant `*.*` at `any` scope to `platform_owner` (D27). C-04's `role_permission` SHALL NOT include a mapping for `platform_owner` (D27).

Trace: D27, D28, AC-6, AC-18, AC-19.

#### Scenario: Platform Owner can call any endpoint
- **WHEN** a Platform Owner (roles=["platform_owner"]) calls `require_permission` for any resource and action
- **THEN** Casbin enforces with `*` wildcard and `any` scope → passes → no 403

#### Scenario: platform_owner role row exists in C-02's role table
- **WHEN** C-04 migration 004 is applied
- **THEN** C-02's `role` table contains a row with `name = 'platform_owner'`

#### Scenario: platform_owner is NOT in C-04's role_permission
- **WHEN** querying `role_permission` for the `platform_owner` role
- **THEN** the result set is empty — `platform_owner` gets its permissions from C-01's D11 Casbin policies, not from the `role_permission` mapping

### Requirement: Ownership Enforcement (App-Level)

For C-02 profile endpoints (`user.read`, `user.update`), the `require_permission` dependency SHALL additionally enforce an ownership check when the `owner_id` parameter is provided (D12, D22). If `owner_id != ctx.user_id` and the calling user's role does NOT have `institution` scope (admin-level bypass), the dependency SHALL raise HTTP 403 "You can only access your own profile" (D22).

Trace: D12, D22, AC-9, AC-10.

#### Scenario: User can read their own profile
- **WHEN** a Teacher (user_id=UUID-A) calls `require_permission("user", "read", owner_id=UUID-A)`
- **THEN** Casbin passes (Teacher has `user.read`), ownership check passes (`owner_id == ctx.user_id`), dependency returns silently

#### Scenario: User cannot read another user's profile
- **WHEN** a Teacher (user_id=UUID-A) calls `require_permission("user", "read", owner_id=UUID-B)`
- **THEN** Casbin passes (Teacher has `user.read`), ownership check fails (`owner_id != ctx.user_id`), admin bypass check: Teacher does NOT have `institution` scope for cross-user access → dependency raises HTTP 403 "You can only access your own profile"

#### Scenario: Admin bypasses ownership check
- **WHEN** an Admin (roles=["Admin"], user_id=UUID-X) calls `require_permission("user", "read", owner_id=UUID-A)`
- **THEN** Casbin passes (Admin has `user.read` at `institution` scope), ownership check fails (`owner_id != ctx.user_id`), but admin bypass: Admin has `institution` scope → dependency returns silently (Admin can read any user at their institution)

### Requirement: All Endpoints Require Authorization

Every C-01 and C-02 endpoint SHALL declare `Depends(require_permission(resource, action, ...))` with the appropriate resource, action, and object attributes (D16, D31). Lookup endpoints (institution_type, user_category, role list) SHALL also require authorization via their respective read permissions (D31).

Trace: D16, D31, AC-4, AC-14, AC-15.

#### Scenario: Every C-01 endpoint has require_permission
- **WHEN** a request hits any C-01 endpoint (client, institution, org_unit, institution_type, lookup)
- **THEN** the endpoint includes `Depends(require_permission(..., ...))` and authorization is enforced before the service logic runs

#### Scenario: Every C-02 endpoint has require_permission
- **WHEN** a request hits any C-02 endpoint (user, user_profile, role_assignment, user_identifier, user_category, role lookup)
- **THEN** the endpoint includes `Depends(require_permission(..., ...))` and authorization is enforced before the service logic runs

#### Scenario: Unauthenticated requests are rejected before authorization
- **WHEN** a request with no JWT hits a protected endpoint
- **THEN** the C-03 middleware returns 401 before `require_permission` runs (authentication precedes authorization)

### Requirement: Import and Dependency Integrity

C-04's `kernel/authz/` package SHALL only import from `kernel/` packages and standard library / third-party packages. It SHALL NOT import from `business/` or `shared/` (A3, D32). The dependency graph SHALL remain acyclic: C-04 (Level 3) may import from C-02 (Level 2) and C-01a (Level 1). Lower levels SHALL NOT import from C-04 (A4, D32).

Trace: D9, D32, AC-20, AC-21.

#### Scenario: kernel/authz/ does not import from business/
- **WHEN** running import-linter
- **THEN** the A3 contract (`kernel → ∅`) passes — no imports from `business/` or `shared/` in `kernel/authz/`

#### Scenario: Dependency graph is acyclic
- **WHEN** running import-linter
- **THEN** the A4 contract (`acyclic`) passes — the dependency graph has no cycles involving C-04

### Requirement: Authorization Tests Use Real Casbin

C-04 tests SHALL build a Casbin enforcer with the real model and real seed policies, then assert `enforcer.enforce(subject, object, action)` returns true or false for each role-permission-scope combination (D17). The `require_permission` dependency SHALL be tested in isolation with a known TenantContext.

Trace: D17, AC-22, AC-23.

#### Scenario: Unit tests validate each role's allowed permissions
- **WHEN** running C-04's test suite
- **THEN** for each of the 7 C-02 roles, the tests assert which permissions the enforcer grants and which it denies, using the real Casbin enforcer

#### Scenario: require_permission dependency is tested in isolation
- **WHEN** running C-04's test suite
- **THEN** the dependency is tested with a mocked TenantContext carrying known role labels, asserting 403 for unauthorized and success for authorized

### Requirement: C-01 Casbin Model Relocation

The file `business/tenant_institution/casbin_model.conf` SHALL be moved to `kernel/authz/casbin_model.conf` (D14). C-01's `build_enforcer()` function SHALL be removed (D14). C-01's `register_casbin_policies(enforcer)` hook SHALL continue to add D11 policies using the central enforcer provided by C-04 (D14).

Trace: D4, D14, D25, AC-16, AC-17.

#### Scenario: Model file exists at the new location
- **WHEN** C-04 migration/refactor is applied
- **THEN** `kernel/authz/casbin_model.conf` exists and contains the same Casbin model content as the original C-01 file

#### Scenario: build_enforcer() is removed
- **WHEN** searching the codebase for `build_enforcer`
- **THEN** the function no longer exists in C-01's `policies.py` or anywhere else

#### Scenario: C-01 policies are still registered
- **WHEN** the app starts and the factory calls `register_casbin_policies(enforcer)` on C-01's manifest
- **THEN** C-01's D11 tiered-delegation policies (platform_owner, client_director, institution_admin, cross_institution) are added to the central enforcer
