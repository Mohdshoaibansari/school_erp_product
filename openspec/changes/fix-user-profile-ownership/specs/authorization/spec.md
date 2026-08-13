## Purpose

This delta spec modifies C-04 Authorization to introduce the `user_profile.admin` permission and remove Stage 5 (ownership check) from `_check_impl`. The two-tier model uses Stage 3 (self-service bypass) and Stage 4 (Casbin `user_profile.admin`) to handle all profile authorization scenarios.

**Delta type:** MODIFIED
**Base spec:** `openspec/changes/archive/2026-07-14-add-c04-authorization/specs/authorization/spec.md`
**Decisional source:** D13 (UserProfile self-service & admin management)

---

## Requirements

### Requirement: New user_profile.admin Permission

The `permission` table SHALL include a `user_profile.admin` permission (resource=`user_profile`, action=`admin`). This single permission replaces the per-action permissions (`user_profile.create/read/update`) for non-self profile access.

Trace: D13-a, AC-2.

#### Scenario: user_profile.admin permission exists
- **WHEN** querying the `permission` table for `name = 'user_profile.admin'`
- **THEN** a row is returned with `resource = 'user_profile'` and `action = 'admin'`

### Requirement: Role-Permission Mapping for user_profile.admin

The `role_permission` table SHALL map `user_profile.admin` to Admin, client_director, and institution_admin roles. No other roles receive this permission.

**Admin, client_director, institution_admin:**
- `user_profile.admin` (institution scope for Admin/institution_admin, tenant scope for client_director)

**Teacher, Staff, Student, Parent:**
- No `user_profile.admin` — they use Stage 3 self-service bypass for their own profile

Trace: D13-a, AC-2, AC-4, AC-5.

#### Scenario: Admin has user_profile.admin
- **WHEN** querying `role_permission` for the Admin role
- **THEN** the result set includes `user_profile.admin`

#### Scenario: client_director has user_profile.admin
- **WHEN** querying `role_permission` for the client_director role
- **THEN** the result set includes `user_profile.admin`

#### Scenario: institution_admin has user_profile.admin
- **WHEN** querying `role_permission` for the institution_admin role
- **THEN** the result set includes `user_profile.admin`

#### Scenario: Teacher does NOT have user_profile.admin
- **WHEN** querying `role_permission` for the Teacher role
- **THEN** the result set does NOT include `user_profile.admin`

#### Scenario: Student does NOT have user_profile.admin
- **WHEN** querying `role_permission` for the Student role
- **THEN** the result set does NOT include `user_profile.admin`

### Requirement: Remove Stage 5 (Ownership Check) from _check_impl

The `_check_impl` function in `authz/dependencies.py` SHALL remove Stage 5 (the ownership/admin bypass check). The revised authorization flow is:

1. **Stage 1:** Platform owner bypass
2. **Stage 2:** Role validation
3. **Stage 3:** Self-service bypass — if `owner_id is not None and owner_id == ctx.user_id`, pass immediately (no Casbin)
4. **Stage 4:** Casbin enforcement — check the user's role-permission mapping

Stage 5 (ownership check with admin bypass) is deleted. Casbin at Stage 4 handles admin access via `user_profile.admin` permission.

Trace: D13-b, AC-6.

#### Scenario: Stage 5 removed from _check_impl
- **WHEN** inspecting `_check_impl` in `authz/dependencies.py`
- **THEN** there is no ownership/admin bypass stage after the Casbin check

#### Scenario: Self-service at Stage 3
- **WHEN** `owner_id == ctx.user_id` is passed to `_check_impl`
- **THEN** the function returns successfully at Stage 3 without reaching Casbin

#### Scenario: Admin access via Casbin at Stage 4
- **WHEN** `owner_id != ctx.user_id` and the user has `user_profile.admin` in Casbin
- **THEN** the function returns successfully at Stage 4

#### Scenario: Non-admin cross-user denied at Stage 4
- **WHEN** `owner_id != ctx.user_id` and the user does NOT have `user_profile.admin` in Casbin
- **THEN** the function raises HTTP 403 at Stage 4

### Requirement: Profile Routes Use user_profile.admin for Non-Self Access

Profile endpoints SHALL pass `owner_id=user_id` to `require_permission` / `check_permission`. The action parameter for Casbin check SHALL be `admin` (not `create`/`read`/`update`), since the single `user_profile.admin` permission governs all non-self profile operations.

Trace: D13-a, AC-2, AC-4, AC-5.

#### Scenario: POST endpoint checks user_profile.admin for non-self
- **WHEN** `POST /api/v1/users/{id}/profile` is called with `owner_id != ctx.user_id`
- **THEN** the endpoint checks `user_profile.admin` via Casbin at Stage 4

#### Scenario: GET endpoint checks user_profile.admin for non-self
- **WHEN** `GET /api/v1/users/{id}/profile` is called with `owner_id != ctx.user_id`
- **THEN** the endpoint checks `user_profile.admin` via Casbin at Stage 4

#### Scenario: PATCH endpoint checks user_profile.admin for non-self
- **WHEN** `PATCH /api/v1/users/{id}/profile` is called with `owner_id != ctx.user_id`
- **THEN** the endpoint checks `user_profile.admin` via Casbin at Stage 4

### Requirement: Migration for user_profile.admin Permission and Role Mappings

Alembic migration 019 (or equivalent) SHALL insert the `user_profile.admin` permission and map it to Admin, client_director, and institution_admin roles. The migration SHALL be idempotent.

Trace: D13-a, AC-2.

#### Scenario: Migration inserts user_profile.admin permission
- **WHEN** migration 019 is applied
- **THEN** the `permission` table contains a row with `name = 'user_profile.admin'`

#### Scenario: Migration maps user_profile.admin to admin roles
- **WHEN** migration 019 is applied
- **THEN** the `role_permission` table contains `user_profile.admin` mappings for Admin, client_director, and institution_admin

#### Scenario: Migration is idempotent
- **WHEN** migration 019 is applied twice
- **THEN** no duplicate entries are created in `permission` or `role_permission` tables
