## ADDED Requirements

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
