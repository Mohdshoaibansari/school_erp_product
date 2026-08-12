## Purpose

This delta spec modifies C-04 Authorization to add role-permission mappings for UserProfile operations. It ensures that all roles have appropriate permissions for profile self-service while maintaining admin-level control for creating profiles on behalf of users.

**Delta type:** MODIFIED
**Base spec:** `openspec/changes/archive/2026-07-14-add-c04-authorization/specs/authorization/spec.md`
**Decisional source:** D13 (UserProfile self-service & ownership)

---

## Requirements

### Requirement: Permission Catalog Update

The `permission` table SHALL include `user_profile.create` in addition to the existing `user_profile.read` and `user_profile.update` permissions. The total C-02 permissions SHALL be 13 (previously 12).

Trace: D13, AC-3.

#### Scenario: user_profile.create permission exists
- **WHEN** querying the `permission` table for `name = 'user_profile.create'`
- **THEN** a row is returned with `resource = 'user_profile'` and `action = 'create'`

#### Scenario: Total C-02 permissions count
- **WHEN** querying the `permission` table for permissions where `resource` starts with `user`, `role_assignment`, or `user_identifier`
- **THEN** the count is 13 (previously 12)

### Requirement: Role-Permission Mapping for UserProfile

The `role_permission` table SHALL be updated to include the following mappings for UserProfile permissions:

**Admin, client_director, institution_admin:**
- `user_profile.create` (institution scope)
- `user_profile.read` (institution scope)
- `user_profile.update` (institution scope)

**Teacher, Staff, Student, Parent:**
- `user_profile.read` (institution scope)
- `user_profile.update` (institution scope)

Note: Teacher, Staff, Student, Parent do NOT get `user_profile.create` — they can create their own profile via self-ownership check, but cannot create profiles for other users.

Trace: D13, AC-2, AC-3.

#### Scenario: Admin has all user_profile permissions
- **WHEN** querying `role_permission` for the Admin role
- **THEN** the result set includes `user_profile.create`, `user_profile.read`, and `user_profile.update`

#### Scenario: Teacher has user_profile.read and user_profile.update
- **WHEN** querying `role_permission` for the Teacher role
- **THEN** the result set includes `user_profile.read` and `user_profile.update` but NOT `user_profile.create`

#### Scenario: Student has user_profile.read and user_profile.update
- **WHEN** querying `role_permission` for the Student role
- **THEN** the result set includes `user_profile.read` and `user_profile.update` but NOT `user_profile.create`

#### Scenario: Parent has user_profile.read and user_profile.update
- **WHEN** querying `role_permission` for the Parent role
- **THEN** the result set includes `user_profile.read` and `user_profile.update` but NOT `user_profile.create`

#### Scenario: client_director has all user_profile permissions
- **WHEN** querying `role_permission` for the client_director role
- **THEN** the result set includes `user_profile.create`, `user_profile.read`, and `user_profile.update`

#### Scenario: institution_admin has all user_profile permissions
- **WHEN** querying `role_permission` for the institution_admin role
- **THEN** the result set includes `user_profile.create`, `user_profile.read`, and `user_profile.update`

### Requirement: Ownership Check Integration with require_permission

The `require_permission` dependency SHALL support an `owner_id` parameter for ownership enforcement. When `owner_id` is provided:
1. If `owner_id == ctx.user_id`, the check passes (self-access)
2. If `owner_id != ctx.user_id`, the check falls through to Casbin enforcement
3. If Casbin enforcement passes (user has the permission with institution scope), the check passes (admin bypass)
4. If Casbin enforcement fails, the dependency raises HTTP 403

Trace: D13-a, AC-5, AC-6, AC-7.

#### Scenario: Self-access bypasses Casbin for profile operations
- **WHEN** a Teacher (user_id=UUID-A) calls `require_permission("user_profile", "read", owner_id=UUID-A)`
- **THEN** the ownership check passes (`owner_id == ctx.user_id`), Casbin is not consulted, and the dependency returns silently

#### Scenario: Non-self access requires Casbin enforcement
- **WHEN** a Teacher (user_id=UUID-A) calls `require_permission("user_profile", "read", owner_id=UUID-B)`
- **THEN** the ownership check fails (`owner_id != ctx.user_id`), Casbin is consulted, Teacher does NOT have cross-user profile access, and the dependency raises HTTP 403

#### Scenario: Admin bypasses ownership check via institution scope
- **WHEN** an Admin (user_id=UUID-X, institution_id=SchoolA) calls `require_permission("user_profile", "read", owner_id=UUID-A)`
- **THEN** the ownership check fails (`owner_id != ctx.user_id`), Casbin is consulted, Admin has `user_profile.read` at institution scope, and the dependency returns silently

### Requirement: Migration for Role-Permission Seed Data

Alembic migration 019 (or equivalent) SHALL insert the new `user_profile.create` permission and update role-permission mappings for all roles. The migration SHALL be idempotent — re-running it should not create duplicate entries.

Trace: D13, AC-2, AC-3.

#### Scenario: Migration inserts user_profile.create permission
- **WHEN** migration 019 is applied
- **THEN** the `permission` table contains a row with `name = 'user_profile.create'`

#### Scenario: Migration updates role-permission mappings
- **WHEN** migration 019 is applied
- **THEN** the `role_permission` table contains the new mappings for Admin, client_director, institution_admin, Teacher, Staff, Student, and Parent roles

#### Scenario: Migration is idempotent
- **WHEN** migration 019 is applied twice
- **THEN** no duplicate entries are created in `permission` or `role_permission` tables
