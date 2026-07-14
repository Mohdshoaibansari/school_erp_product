## Purpose

This document defines the MODIFIED delta requirements for C-02 Identity & User Management resulting from C-04 Authorization. These changes retrofit all C-02 endpoints with authorization checks and add a `platform_owner` row to C-02's `role` table. The behavioral contract of every C-02 endpoint changes: they now require a specific permission before executing. The base C-02 spec is at `openspec/specs/identity-user-management/spec.md` (archived 2026-07-11-add-c02-identity-user-management).

## Modified Requirements

### Requirement: C-02 Endpoints Require Authorization (MODIFIED)

All C-02 route handlers SHALL include `Depends(require_permission(resource, action, client_id=..., institution_id=..., owner_id=...))` where `resource` and `action` correspond to the endpoint's operation (D16). An endpoint that previously accepted any authenticated request SHALL now return HTTP 403 if the calling user's role lacks the required permission or if Casbin scope checks fail (D5, D6).

Profile read/update endpoints (`user.read`, `user.update`) SHALL additionally pass the `owner_id` parameter for ownership enforcement (D22). For `user.read` on `/api/v1/users/{user_id}`, the `owner_id` SHALL be the path parameter. For `user.update` on `/api/v1/users/{user_id}`, the `owner_id` SHALL be the path parameter.

Lookup endpoints (`user_category`, `role` list) SHALL also require authorization via their respective read permissions (`user.read` and `role_assignment.read` respectively) (D31).

**Endpoint-to-permission mapping:**

| Endpoint | Resource | Action | Object Attributes |
|---|---|---|---|
| `GET /api/v1/users` | `user` | `read` | `client_id=ctx` |
| `POST /api/v1/users` | `user` | `create` | `client_id=ctx, institution_id=body` |
| `GET /api/v1/users/{user_id}` | `user` | `read` | `client_id=ctx, institution_id=ctx, owner_id=path` |
| `PUT /api/v1/users/{user_id}` | `user` | `update` | `client_id=ctx, institution_id=ctx, owner_id=path` |
| `POST /api/v1/users/{user_id}/transition` | `user` | `suspend` | `client_id=ctx` |
| `POST /api/v1/users/{user_id}/profile` | `user_profile` | `read` | `client_id=ctx` |
| `PUT /api/v1/users/{user_id}/profile` | `user_profile` | `update` | `client_id=ctx` |
| `GET /api/v1/users/{user_id}/roles` | `role_assignment` | `read` | `client_id=ctx` |
| `POST /api/v1/users/{user_id}/roles` | `role_assignment` | `create` | `client_id=ctx` |
| `DELETE /api/v1/users/{user_id}/roles/{assignment_id}` | `role_assignment` | `delete` | `client_id=ctx` |
| `GET /api/v1/users/{user_id}/identifiers` | `user_identifier` | `read` | `client_id=ctx` |
| `POST /api/v1/users/{user_id}/identifiers` | `user_identifier` | `create` | `client_id=ctx` |
| `DELETE /api/v1/users/{user_id}/identifiers/{identifier_id}` | `user_identifier` | `delete` | `client_id=ctx` |
| `GET /api/v1/user-categories` | `user` | `read` | `client_id=ctx` |
| `GET /api/v1/roles` | `role_assignment` | `read` | `client_id=ctx` |

Trace: D16, D5, D19, D22, D31, AC-15.

#### Scenario: Authorized admin creates a user
- **WHEN** an Institution Admin (roles=["Admin"]) calls `POST /api/v1/users` with valid body for their own institution
- **THEN** `require_permission("user", "create", client_id=ctx.client_id, institution_id=body.institution_id)` passes, and the endpoint creates the user → returns 201

#### Scenario: Unauthorized teacher cannot create a user
- **WHEN** a Teacher (roles=["Teacher"]) calls `POST /api/v1/users`
- **THEN** `require_permission("user", "create", ...)` runs, Casbin denies (Teacher lacks `user.create`), and the endpoint returns 403

#### Scenario: User can read their own profile
- **WHEN** a Teacher (user_id=UUID-A) calls `GET /api/v1/users/UUID-A`
- **THEN** Casbin passes (Teacher has `user.read`), ownership check passes (`owner_id UUID-A == ctx.user_id UUID-A`), and the endpoint returns 200

#### Scenario: User cannot read another user's profile
- **WHEN** a Teacher (user_id=UUID-A) calls `GET /api/v1/users/UUID-B`
- **THEN** Casbin passes (Teacher has `user.read`), ownership check fails (`owner_id UUID-B != ctx.user_id UUID-A`), admin bypass check: Teacher lacks `institution` scope → endpoint returns 403 "You can only access your own profile"

#### Scenario: Lookup endpoint requires authorization
- **WHEN** a Teacher (roles=["Teacher"]) calls `GET /api/v1/roles`
- **THEN** `require_permission("role_assignment", "read", ...)` passes (Teacher has `role_assignment.read`), and the endpoint returns the role list

### Requirement: Platform Owner Role Row (MODIFIED)

C-02's `role` lookup table SHALL contain one new row: `platform_owner` (D28). This row SHALL be inserted by C-04's migration 004 (not by a C-02 migration). The row SHALL be assigned to the platform owner user via `role_assignment` by the C-03 bootstrap CLI (C-03 D30). C-04's `role_permission` table SHALL NOT include any mapping for this role — it receives `*.*` permissions from C-01's D11 Casbin policies (D27).

Trace: D27, D28, AC-18, AC-19.

#### Scenario: platform_owner exists in the role table
- **WHEN** C-04 migration 004 is applied
- **THEN** the `role` table contains a row with `name = 'platform_owner'`

#### Scenario: platform_owner is not mapped in role_permission
- **WHEN** querying `role_permission JOIN role` for `name = 'platform_owner'`
- **THEN** the result set is empty — no `role_permission` rows reference the `platform_owner` role

#### Scenario: Platform Owner role is assignable
- **WHEN** the C-03 bootstrap CLI creates the platform owner user
- **THEN** a `role_assignment` row is created linking the platform owner user_id to the `platform_owner` role_id, and subsequent requests from this user have `roles = ["platform_owner"]` in their TenantContext

### Requirement: C-02 Tests Adapted for Authorization (MODIFIED)

Existing C-02 tests SHALL continue to pass after retrofit (D20). Test fixtures SHALL include sufficient seed data (`role`, `permission`, `role_permission` rows) so that the `require_permission` dependency does not block authorized operations, OR tests SHALL use `app.dependency_overrides[get_enforcer]` to bypass authorization for tests that do not exercise C-04 directly (D20).

Trace: D16, D20, AC-24.

#### Scenario: C-02 tests continue to pass
- **WHEN** running the complete C-02 test suite after C-04 retrofit
- **THEN** all existing C-02 tests pass — no unauthorized 403 errors from `require_permission` for tests that simulate authorized operations

#### Scenario: Tests use appropriate role context
- **WHEN** a C-02 test creates a user via the API (e.g., `POST /api/v1/users`)
- **THEN** the test's TenantContext includes a role (e.g., `Admin`) that has `user.create`, either via seed data or dependency override
