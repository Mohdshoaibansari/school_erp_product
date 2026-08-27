# platform-owner-separation Specification

## Purpose
TBD - created by archiving change add-platform-owner-separation. Update Purpose after archive.
## Requirements
### Requirement: Platform owner identity in Supabase Auth only
The platform owner SHALL exist only in Supabase Auth with `user_metadata.is_platform_owner = true`. The platform owner MUST NOT have a row in the `app_user` table.

#### Scenario: Platform owner login without app_user row
- **WHEN** a Supabase Auth user with `user_metadata.is_platform_owner = true` logs in
- **THEN** the system SHALL skip the `app_user` table lookup entirely
- **AND** return a JWT with `{sub: <user_id>, is_platform_owner: true}`

#### Scenario: Normal user login still requires app_user row
- **WHEN** a Supabase Auth user without `is_platform_owner` metadata logs in
- **THEN** the system SHALL look up the user in `app_user` as before
- **AND** enforce lifecycle_status and cross-tenant checks

### Requirement: Platform owner JWT claims
The platform owner's JWT SHALL contain only `sub` (user_id) and `is_platform_owner: true`. It MUST NOT contain `client_id` or `institution_id`.

#### Scenario: Platform owner JWT has no tenant binding
- **WHEN** a platform owner logs in successfully
- **THEN** the JWT payload SHALL include `is_platform_owner: true`
- **AND** the JWT payload SHALL NOT include `client_id` or `institution_id`

### Requirement: Platform owner login response
The login response for platform owner SHALL include `is_platform_owner: true`. The field MUST NOT be present for normal users.

#### Scenario: Platform owner login response includes flag
- **WHEN** platform owner logs in successfully
- **THEN** the response SHALL contain `"is_platform_owner": true`

#### Scenario: Normal user login response does not include flag
- **WHEN** a normal user logs in successfully
- **THEN** the response SHALL NOT contain the `is_platform_owner` field

### Requirement: Platform owner middleware detection
The middleware SHALL detect platform owner ONLY from the JWT claim `is_platform_owner: true`. It MUST NOT use DB role lookup or path prefix detection.

#### Scenario: Middleware sets platform owner context from JWT
- **WHEN** a request arrives with a JWT containing `is_platform_owner: true`
- **THEN** the middleware SHALL set `TenantContext(is_platform_owner=True, client_id=None, institution_id=None, roles=[])`

#### Scenario: Middleware skips subdomain resolution for platform owner
- **WHEN** a request arrives with a platform owner JWT and no Host header
- **THEN** the middleware SHALL NOT attempt subdomain resolution

### Requirement: Platform owner endpoint access control
The platform owner SHALL only access paths in the configurable whitelist (e.g., `/api/v1/platform/`, `/api/auth/`, `/health`). Access to any other path with `client_id=None` SHALL return 403.

#### Scenario: Platform owner accesses platform endpoint
- **WHEN** platform owner requests `/api/v1/platform/clients`
- **THEN** the request SHALL proceed normally

#### Scenario: Platform owner blocked from tenant endpoint
- **WHEN** platform owner requests `/api/v1/fees` with `client_id=None`
- **THEN** the middleware SHALL return 403 Forbidden

### Requirement: require_platform_owner JWT validation
The `require_platform_owner` dependency SHALL decode the JWT from the `Authorization` header and verify the `is_platform_owner: true` claim directly, independently of the middleware's TenantContext.

#### Scenario: Dependency validates JWT claim directly
- **WHEN** `require_platform_owner` is invoked
- **THEN** it SHALL extract the JWT from the `Authorization: Bearer <token>` header
- **AND** decode and verify the `is_platform_owner: true` claim
- **AND** return 403 if the claim is absent or false

### Requirement: Repo base skips tenant filter for platform owner
The `_base_query` method SHALL skip the tenant-scoped `client_id` filter when `ctx.is_platform_owner = True`.

#### Scenario: Platform owner queries all records
- **WHEN** a platform owner queries via `IdentityUserService.list_users()`
- **THEN** the tenant filter SHALL be skipped
- **AND** all records across all clients SHALL be returned

### Requirement: Client table RLS with platform owner bypass
The `client` table SHALL have an RLS policy allowing access when `app.is_platform_owner = 'true'`.

#### Scenario: Platform owner bypasses client RLS
- **WHEN** `SET LOCAL app.is_platform_owner = 'true'` is set
- **THEN** the platform owner SHALL see all rows in the `client` table


---
<!-- Synced from add-client-user-bootstrap delta spec -->
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

---
<!-- Synced from add-c02-identity-person-model-revamp delta spec -->
## Person-Model Revamp — Platform Owner Separation

### REQ-POS-01-MOD: Platform Owner Discovery via is_platform_owner (Reinforced — category removed)

The Platform Owner SHALL exist only in Supabase Auth with `user_metadata.is_platform_owner = true` and MUST NOT have a row in `app_user` — this is **already** the model in the archived spec and is unchanged. The revamp's contribution is that **no residual `user_category`-based discovery code SHALL remain**. Platform Owner discovery SHALL use the `is_platform_owner` flag/claim exclusively (AC-13). Per D6a.

#### Scenario: PO discovered by flag (unchanged, reinforced)
- **WHEN** the system checks whether a user is a Platform Owner
- **THEN** it SHALL check the `is_platform_owner` flag/claim
- **AND** SHALL NOT consult any `user_category` value (the column no longer exists)

### REQ-POS-02: Platform Owner ↔ Person Linkage (Design clarification)

The PO exists only in Supabase Auth (no `app_user`, no `client_user` row). Whether the PO gets a `person` row for their own human data is an **open design clarification** (PRD §3 implies "PO's own human data now lives on `person`" but no AC covers it). This delta flags the clarification for the design phase. Per D3a, D6a.

> **Design clarification needed (deferred to design.md):** Does the PO (who has no account row) get a `person` row? If yes, how is it linked (the PO has no `app_user.person_id`/`client_user.person_id`)? Options: (a) PO gets a `person` row linked via a PO-specific mechanism; (b) PO has no `person` row (human data is not modeled for the PO in this revamp). This is minor — the PO is a single SaaS operator, not a domain entity.