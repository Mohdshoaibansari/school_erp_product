## Purpose

This document defines the MODIFIED delta requirements for C-01 Tenant & Institution Management resulting from C-04 Authorization. These changes retrofit all C-01 endpoints with authorization checks and relocate the Casbin model to the centralized C-04 location. The behavioral contract of every C-01 endpoint changes: they now require a specific permission before executing. The base C-01 spec is at `openspec/specs/tenant-institution/spec.md` (archived 2026-07-08-refactor-c01-kernel-business-split).

## Modified Requirements

### Requirement: C-01 Endpoints Require Authorization (MODIFIED)

All C-01 route handlers SHALL include `Depends(require_permission(resource, action, client_id=..., institution_id=...))` where `resource` and `action` correspond to the endpoint's operation and `client_id`/`institution_id` are extracted from the request (path param, body, or query) (D16). An endpoint that previously accepted any authenticated request SHALL now return HTTP 403 if the calling user's role lacks the required permission or if Casbin scope checks fail (D5, D6).

**Endpoint-to-permission mapping:**

| Endpoint | Resource | Action | Object Attributes |
|---|---|---|---|
| `GET /api/v1/clients` (platform) | `client` | `read` | `client_id=*` (any) |
| `PUT /api/v1/clients/{client_id}` | `client` | `update` | `client_id=path` |
| `POST /api/v1/clients/{client_id}/transition-lifecycle` | `client` | `transition_lifecycle` | `client_id=path` |
| `POST /api/v1/clients/{client_id}/transfer-ownership` | `client` | `transfer_ownership` | `client_id=path` |
| `GET /api/v1/institutions` | `institution` | `read` | `client_id=ctx.client_id` |
| `POST /api/v1/institutions` | `institution` | `create` | `client_id=body, institution_id=optimistic` |
| `GET /api/v1/institutions/{institution_id}` | `institution` | `read` | `client_id=ctx, institution_id=path` |
| `PUT /api/v1/institutions/{institution_id}` | `institution` | `update` | `client_id=ctx, institution_id=path` |
| `POST /api/v1/institutions/{institution_id}/transition-lifecycle` | `institution` | `transition_lifecycle` | `client_id=ctx, institution_id=path` |
| `GET /api/v1/org-units` | `org_unit` | `read` | `client_id=ctx` |
| `POST /api/v1/org-units` | `org_unit` | `create` | `client_id=ctx, institution_id=body` |
| `GET /api/v1/org-units/{org_unit_id}` | `org_unit` | `read` | `client_id=ctx` |
| `PUT /api/v1/org-units/{org_unit_id}` | `org_unit` | `update` | `client_id=ctx` |
| `DELETE /api/v1/org-units/{org_unit_id}` | `org_unit` | `delete` | `client_id=ctx` |
| `POST /api/v1/org-units/{org_unit_id}/move` | `org_unit` | `move` | `client_id=ctx` |
| `GET /api/v1/institution-types` | `institution_type` | `read` | `client_id=ctx` |

Trace: D16, D5, D19, D31, AC-14.

#### Scenario: Authorized admin creates an institution
- **WHEN** an Institution Admin (roles=["Admin"]) calls `POST /api/v1/institutions` with valid body for their own institution
- **THEN** `require_permission("institution", "create", client_id=ctx.client_id)` passes, and the endpoint creates the institution → returns 201

#### Scenario: Unauthorized teacher cannot create an institution
- **WHEN** a Teacher (roles=["Teacher"]) calls `POST /api/v1/institutions`
- **THEN** `require_permission("institution", "create", ...)` runs, Casbin denies (Teacher lacks `institution.create`), and the endpoint returns 403

#### Scenario: Cross-institution update is blocked
- **WHEN** an Admin at School A calls `PUT /api/v1/institutions/{institution_id}` where the institution belongs to School B
- **THEN** Casbin checks `sub.institution_id (SchoolA) == obj.institution_id (SchoolB)` → fails → endpoint returns 403

### Requirement: Casbin Model Relocation (MODIFIED)

The Casbin model file SHALL be located at `kernel/authz/casbin_model.conf` (D14, D4). The file SHALL be removed from its previous location at `business/tenant_institution/casbin_model.conf` (D14). C-01's `register_casbin_policies(enforcer)` hook SHALL receive the central enforcer from the app factory (created from the relocated model) and SHALL add the D11 tiered-delegation policies to it (D14).

Trace: D4, D14, AC-17.

#### Scenario: Model file is at the new location
- **WHEN** the C-04 change is applied
- **THEN** the Casbin model exists at `kernel/authz/casbin_model.conf` and does NOT exist at `business/tenant_institution/casbin_model.conf`

#### Scenario: C-01 policies are registered against the central enforcer
- **WHEN** the app starts
- **THEN** C-01's `register_casbin_policies(enforcer)` hook adds the D11 policies (platform_owner `*.*` at `any` scope, client_director own-client, institution_admin own-institution, etc.) to the enforcer created from `kernel/authz/casbin_model.conf`

### Requirement: C-01 build_enforcer() Removed (MODIFIED)

C-01's `build_enforcer()` function SHALL be removed (D14). Any test code that previously called `build_enforcer()` to obtain a Casbin enforcer SHALL instead use the centrally-provided enforcer via `get_enforcer()` or a test fixture that creates it from the relocated model (D14, D17).

Trace: D14, AC-16.

#### Scenario: build_enforcer() no longer exists
- **WHEN** searching C-01's `policies.py` or any other file in the `business/tenant_institution/` package
- **THEN** the function `build_enforcer` is not defined

#### Scenario: C-01 Casbin tests use the central enforcer
- **WHEN** running C-01's Casbin permission tests (`test_casbin_permissions.py`)
- **THEN** the tests create an enforcer from the relocated model at `kernel/authz/casbin_model.conf` and register C-01 policies via `register_policies(enforcer)`, then assert enforcement results — without calling a removed `build_enforcer()` function

### Requirement: C-01 Tests Adapted for Authorization (MODIFIED)

Existing C-01 tests SHALL continue to pass after retrofit (D20). Test fixtures SHALL include sufficient seed data (`role`, `permission`, `role_permission` rows) so that the `require_permission` dependency does not block authorized operations, OR tests SHALL use `app.dependency_overrides[get_enforcer]` to bypass authorization for tests that do not exercise C-04 directly (D20).

Trace: D16, D20, AC-24.

#### Scenario: C-01 tests continue to pass
- **WHEN** running the complete C-01 test suite after C-04 retrofit
- **THEN** all existing C-01 tests pass — no unauthorized 403 errors from `require_permission` for tests that simulate authorized operations

#### Scenario: Tests use appropriate role context
- **WHEN** a C-01 test creates a user via the API (e.g., `POST /api/v1/institutions`)
- **THEN** the test's TenantContext includes a role (e.g., `Admin` or `institution_admin`) that has the required permission, either via seed data or dependency override
