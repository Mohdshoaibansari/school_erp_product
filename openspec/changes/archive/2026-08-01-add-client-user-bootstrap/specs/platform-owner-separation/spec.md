## MODIFIED Requirements

### Requirement: Platform owner endpoint access control

The platform owner SHALL only access paths in the configurable whitelist (`config.PLATFORM_PATHS` — currently `/api/v1/platform/`, `/api/v1/config/`, `/api/v1/lookups/`, `/api/auth/`, `/health`, `/docs`, `/openapi.json`). Access to any other path with `client_id=None` SHALL return `403 Platform owner access restricted to platform endpoints`.

**Widened for the `client-user-bootstrap` capability:** the nested endpoint surface `/api/v1/platform/clients/{client_id}/users/*` (POST bootstrap, GET list, PATCH transition, DELETE revoke) SHALL be reachable by the Platform Owner without a `Host` header. All four nested endpoints SHALL use the `require_platform_owner` dependency (NOT `require_permission`), decoupling them from the Casbin role-permission check the way existing `/api/v1/platform/clients` endpoints already are. The PO's `require_permission` bypass (per D28) is unchanged for ALL endpoints — defense-in-depth keeps the bypass at the gate while RLS remains the actual wall on institution tables.

#### Scenario: Platform owner accesses nested platform clients/users endpoint
- **WHEN** platform owner requests `POST /api/v1/platform/clients/$ID/users` with a PO JWT and no Host header
- **THEN** the `require_platform_owner` dependency SHALL admit the request
- **AND** the request SHALL proceed to the bootstrap service

#### Scenario: Non-PO token rejected on nested endpoint
- **WHEN** a CD or Institution Admin JWT calls `POST /api/v1/platform/clients/$ID/users`
- **THEN** the `require_platform_owner` dependency SHALL reject with `403 Forbidden`

#### Scenario: Platform owner blocked from tenant endpoint (unchanged)
- **WHEN** platform owner requests `/api/v1/fees` with `client_id=None`
- **THEN** the middleware SHALL return `403 Platform owner access restricted to platform endpoints`
- **AND** this behavior is unchanged from the prior spec

### Requirement: Client table RLS with platform owner bypass

The `client` table SHALL have an RLS policy allowing access when `app.is_platform_owner = 'true'` is set. **Widened for the `client-user-bootstrap` capability:** an analogous RLS policy SHALL apply to the new `client_user` table — the PO (with `app.is_platform_owner = 'true'`) SHALL bypass the `client_id = current_client_id()` filter on `client_user` and SHALL have full CRUD access to every row across all clients. This RLS bypass is ONLY for `client_user` — the institution-scoped tables (`app_user`, `institution`, `org_unit`, `role_assignment`, `homework`, `fees`, `submission`, `grade`) keep their existing RLS policies unchanged (the PO has no `app.current_client_id` so those policies still filter to ZERO rows for the PO).

#### Scenario: Platform owner bypasses client_user RLS
- **WHEN** `SET LOCAL app.is_platform_owner = 'true'` is set
- **THEN** `client_user` RLS SHALL allow the PO to SELECT, INSERT, UPDATE, and DELETE any row
- **AND** this bypass SHALL NOT extend to `app_user` (whose RLS stays as-is)

#### Scenario: Platform owner bypasses client RLS (unchanged)
- **WHEN** `SET LOCAL app.is_platform_owner = 'true'` is set
- **THEN** the PO SHALL see all rows in the `client` table
- **AND** this behavior is unchanged from the prior spec

#### Scenario: CD reads own client_user row (not via PO bypass)
- **WHEN** a CD accesses `client_user` with their session context (`app.current_client_id` set from their JWT, `app.is_platform_owner` NOT set)
- **THEN** RLS SHALL permit only their own row (`id = current_user_id()`)
- **AND** this is governed by the `client-user-bootstrap` capability; the PO-bypass RLS stanza above is independent

### Requirement: require_platform_owner JWT validation

The `require_platform_owner` dependency SHALL decode the JWT from the `Authorization` header and verify the `is_platform_owner: true` claim directly. **Widened for the `client-user-bootstrap` capability:** `require_platform_owner` SHALL ALSO protect the nested `/api/v1/platform/clients/{client_id}/users/{user_id}?` endpoint surface (POST, GET, PATCH, DELETE). The dependency itself is unchanged; only the set of routes that depend on it grows.

#### Scenario: Dependency validates JWT claim on nested users endpoints
- **WHEN** any of the nested users endpoints is invoked
- **THEN** `require_platform_owner` SHALL extract the JWT, decode, and verify `is_platform_owner: true`
- **AND** SHALL return `403` if the claim is absent or false

#### Scenario: Dependency unchanged for existing platform clients endpoints
- **WHEN** `require_platform_owner` is invoked on existing `/api/v1/platform/clients/{crud}` endpoints
- **THEN** the behavior SHALL be identical to the prior spec