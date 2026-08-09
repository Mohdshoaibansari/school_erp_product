# authentication — Delta Spec (C-02 User Service Strategy Pattern Refactor)

> **Change:** `refactor-c02-user-service-strategy-pattern`
> **Domain:** C-03 Authentication
> **Delta type:** MODIFIED (login dispatch, activate ordering, request_otp fix, unified `LoginResponse` model, cross-tenant check on CD login)
> **Source:** `docs/architecture/adr-c02-identity-user-management-implementation.md` D6, D9, D10; `docs/architecture/audit-c02-implementation-2026-08-03.md`
> **Predecessor:** `openspec/changes/add-c02-user-creation-activation/specs/authentication/spec.md`

This delta is a MODIFIED evolution of the predecessor spec. The predecessor spec used `## MODIFIED Requirements` headers despite there being no prior baseline spec (per the reviewer's 2026-08-03 finding). This delta explicitly states what is modified relative to the predecessor's own requirements.

---

## MODIFIED Requirements

### Requirement: `AuthService.login` dispatches to a tier-specific JWT-minting flow

The `login` method keeps its public signature and external behavior (returns a unified `LoginResponse`). Internally, it dispatches to a tier-specific JWT-minting flow based on `user_metadata.user_tier` (already present in the predecessor code at `service.py:136-210`):

- PO: custom HS256 JWT with `{sub, is_platform_owner: True}`. No `refresh_token`. This branch already exists in the predecessor.
- CD (client_leadership): custom HS256 JWT with `{sub, user_tier, client_id, role_id}`. This branch already exists as `_login_client_leadership` in the predecessor.
- Institution: Supabase access token from `sign_in_with_password`. This branch already exists in the predecessor.

The dispatch logic is unchanged. What changes in this refactor: the cross-tenant check is added to the CD branch (D10 bug #4), and the login method returns a unified `LoginResponse` model (D9).

#### Scenario: PO login returns `is_platform_owner: True`
- WHEN a Platform Owner logs in successfully
- THEN the response SHALL include `is_platform_owner: true`, `user_tier: null`, `client_id: null`

#### Scenario: CD login returns `user_tier: "client_leadership"` and `client_id`
- WHEN a CD logs in successfully
- THEN the response SHALL include `is_platform_owner: false`, `user_tier: "client_leadership"`, `client_id: <uuid>`

#### Scenario: institution login returns `user_tier: "institution"`
- WHEN an institution user logs in successfully
- THEN the response SHALL include `is_platform_owner: false`, `user_tier: "institution"`, `client_id: <uuid>`

### Requirement: Unified `LoginResponse` with optional tier fields

The `TokenResponse` Pydantic model (which had only `access_token, refresh_token, token_type, expires_in`) is replaced by a unified `LoginResponse` model with optional tier fields:

```python
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    is_platform_owner: bool | None = None
    user_tier: Literal["client_leadership", "institution"] | None = None
    client_id: uuid.UUID | None = None
```

This fixes the predecessor bug where the narrow `TokenResponse` filtered out `is_platform_owner`, `user_tier`, and `client_id` from the response (D9).

#### Scenario: PO response includes `is_platform_owner: true`
- WHEN a PO logs in
- THEN the response JSON SHALL contain `"is_platform_owner": true`

#### Scenario: CD response includes `user_tier` and `client_id`
- WHEN a CD logs in
- THEN the response JSON SHALL contain `"user_tier": "client_leadership"` and `"client_id": "<uuid>"`

#### Scenario: institution response includes `user_tier` and `client_id`
- WHEN an institution user logs in
- THEN the response JSON SHALL contain `"user_tier": "institution"` and `"client_id": "<uuid>"`

### Requirement: `_login_client_leadership` performs a cross-tenant check

`AuthService._login_client_leadership` (or its replacement after the refactor) checks that `ctx.client_id` matches `user_obj.client_id` before minting the CD JWT. This fixes the security gap the 2026-08-03 audit found (a CD from client A could log in from client B's subdomain without rejection).

The institution-user branch already does this check (`service.py:178-186` in the predecessor). This requirement extends the same check to the CD branch.

#### Scenario: CD login from wrong subdomain is rejected with 403
- WHEN a CD with `client_id=X` attempts to log in
- AND the request is on subdomain `Y` (resolves to `client_id=Y` in the `TenantContext`)
- AND `X != Y`
- AND the user is not a Platform Owner
- THEN the auth service SHALL raise `AuthError("Access denied. Account does not belong to this client.", 403)`

#### Scenario: CD login from correct subdomain succeeds
- WHEN a CD with `client_id=X` attempts to log in
- AND the request is on subdomain `X`
- THEN the auth service SHALL mint the custom HS256 JWT and return the unified `LoginResponse`

### Requirement: Activate flow creates Supabase Auth user with password (D11)

The activate flow creates the Supabase Auth user WITH password in a single `POST /auth/v1/admin/users` call, AFTER DB commit. This replaces the previous two-step pattern (create at bootstrap without password → set password at activate via `update_user`). The `update_user` call is removed from the activate flow.

The Supabase call uses the `create_user` method with the `password` parameter:
```python
await self._supabase.create_user(
    user_id, email,
    password=password,
    user_metadata={"user_tier": user_tier},
)
```

The `POST /auth/v1/admin/users` endpoint accepts `password` as an optional body parameter. When provided, the user is created with that password and `email_confirm: True`.

#### Scenario: activate succeeds end-to-end
- WHEN `AuthService.activate` is called with a valid invite token and a valid password
- THEN the strategy SHALL:
  1. Verify the invite token
  2. Look up the user record (CD or institution) in an elevated session
  3. Open a normal session with proper RLS vars
  4. Set `lifecycle_status = "active"` on the user record
  5. Record the lifecycle event
  6. `session.commit()` — DB committed
  7. Call `self._supabase.create_user(user_id, email, password=password, user_metadata={...})` — Supabase user created WITH password
  8. Emit audit event
  9. Return the unified response

#### Scenario: Supabase call fails after DB commit
- WHEN the DB commit succeeds but `self._supabase.create_user` fails
- THEN the system SHALL return an error to the caller
- AND the user record SHALL be in `active` state in the DB
- AND the Supabase Auth user SHALL NOT exist
- AND a retry mechanism (out of scope) SHALL eventually create the Supabase user

#### Scenario: activate no longer calls update_user
- WHEN `AuthService.activate` is called
- THEN the service SHALL NOT call `self._supabase.update_user()` at any point
- AND the password SHALL be passed to `self._supabase.create_user()` at creation time

### Requirement: Activate flow handles the unauthenticated-activate problem (the user is NOT logged in)

When a user clicks the activation link, they are NOT authenticated. There is no JWT in the `Authorization` header. The activate endpoint is in `PLATFORM_PATHS` so the middleware tolerates the missing JWT and sets a subdomain-only `TenantContext` (no `user_id`, possibly a `client_id` from the subdomain).

This creates a problem: the RLS hook in `kernel/db.py` (added by the predecessor's D5-a addendum) reads `_tenant_context_var.get()` and sets `app.current_user_id` from `ctx.user_id` — which is `None` for unauthenticated requests. The RLS policies on `client_user` (`client_user_cd_select_own`) and on `app_user` require `id = current_setting('app.current_user_id')::uuid`. With the value NULL, the user lookup FAILS.

Additionally, the audit emit after a successful activate records `actor=ctx.user_id` — which is `None` — even though we know the activating user (the `sub` claim in the cryptographically signed invite token).

This delta requires the activate flow to:

1. **Decrypt the invite token FIRST** — extract the `user_id` from the verified token. The token is cryptographically signed, so the `user_id` is trusted.

2. **Look up the user's full identity** in a short-lived elevated session (similar to the middleware's subdomain-resolution pattern). The session sets `app.is_platform_owner = 'true'` to bypass RLS during the lookup. The lookup reads the user's `client_id` and `institution_id` from the database.

3. **Use the resolved identity** for the rest of the activate work. The full identity (user_id, client_id, institution_id, user_tier) is held in memory by the activate service. It is NOT written to `_tenant_context_var` (A6 invariant: the contextvar is set only by the middleware).

4. **Set RLS session variables explicitly** for the second session (the one that does the actual activate work). A new public function `set_rls_session_vars(session, *, user_id, client_id, institution_id)` in `kernel/db.py` allows the activate service to set the RLS vars it needs. The session's RLS policies now work correctly because the proper `app.current_user_id`, `app.current_client_id`, and `app.current_institution_id` are set.

5. **Emit audit with the proper actor** — `actor=user_id_from_token`, not `ctx.user_id` (which is `None`).

6. **Return the unified response** — `client_slug` and `user_tier` come from the resolved identity, not from the contextvar.

#### Scenario: activate resolves user from token
- WHEN `AuthService.activate(ctx, invite_token, password)` is called
- AND the request is unauthenticated (no JWT in `Authorization` header)
- AND the invite token is valid
- THEN the service SHALL:
  1. Verify the invite token → extract `user_id` from `sub` claim
  2. Open a short-lived session with `is_platform_owner = 'true'`
  3. Look up the user record: `client_user` (CD) or `app_user` (institution)
  4. Read the user's `client_id` and `institution_id` from the row
  5. Close the elevated session
  6. Open a new session with `set_rls_session_vars(session, user_id=..., client_id=..., institution_id=...)` set explicitly
  7. Do the activate work (lifecycle transition, commit)
  8. Close the session
  9. Call `self._supabase.update_user(...)` to set the password
  10. Emit audit with `actor=user_id_from_token`

#### Scenario: activate finds no user
- WHEN the invite token is valid
- AND no user record exists for the `user_id` in the token
- THEN the service SHALL raise `AuthError("User not found", 404)`

#### Scenario: activate audit actor is the activating user
- WHEN activate succeeds
- THEN the audit emit SHALL have `actor=user_id_from_token` (not `ctx.user_id`, which is `None`)
- AND the audit `client_id` SHALL be the user's `client_id` (from the lookup)
- AND the audit `institution_id` SHALL be the user's `institution_id` (from the lookup, may be `None` for CD)

#### Scenario: set_rls_session_vars helper exists in kernel/db.py
- WHEN the activate service needs to set RLS session variables
- THEN it SHALL call `set_rls_session_vars(session, *, user_id, client_id, institution_id)` from `kernel/db.py`
- AND the function SHALL run `SET LOCAL` statements for each provided variable
- AND the function SHALL be a public utility (any service can call it)
- AND the service is responsible for verifying the values before calling it

### Requirement: Activate route shape — receives the standard `ActivateRequest`

The activate route accepts `ActivateRequest{invite_token, password}` (already present in the predecessor). The route handler is thin: it calls `auth_service.activate(ctx, ...)` and serializes the `ActivateResponse`.

The route does NOT have a separate path for "unauthenticated" vs "authenticated" — it always calls the same service method. The service handles the unauthenticated case internally (via the token-based identity resolution above).

#### Scenario: activate route is thin
- WHEN a POST to `/api/auth/activate` arrives
- THEN the route handler SHALL:
  1. Read `ActivateRequest` from the request body
  2. Call `get_tenant_context()` (returns the middleware's subdomain-only ctx)
  3. Call `auth_service.activate(ctx, request.invite_token, request.password)`
  4. Return the `ActivateResponse` from the service
- AND the route SHALL NOT contain any user-lookup logic

## REMOVED Requirements

- **PO login returns the narrow `TokenResponse` model** — REMOVED. Replaced by `LoginResponse` with tier fields.
- **`_login_client_leadership` skips cross-tenant check** — REMOVED. Cross-tenant check is now mandatory for all tiers.
- **Activate service uses the contextvar's `user_id` for the audit actor** — REMOVED. The audit actor is now the `user_id` from the invite token, not the contextvar.

## Cross-references

- Predecessor spec: `openspec/changes/add-c02-user-creation-activation/specs/authentication/spec.md`
- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6, D9, D10)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
- Related: D5-a addendum (RLS hook); A6 invariant (contextvar set only by middleware)

### Requirement: `request_otp` signature includes `ip_address`

`AuthService.request_otp` signature is updated to include `ip_address: str | None = None` as a keyword-only argument. The route extracts `client_ip` from `http_request` and passes it. This fixes the P1 runtime NameError the 2026-08-03 audit found.

#### Scenario: request_otp no longer raises NameError
- WHEN `AuthService.request_otp(ctx, email, ip_address="1.2.3.4")` is called
- THEN the log line SHALL include `ip=1.2.3.4`
- AND the function SHALL NOT raise `NameError`

#### Scenario: request_otp without ip_address defaults to None
- WHEN `AuthService.request_otp(ctx, email)` is called (no ip_address)
- THEN the function SHALL log `ip=None` and proceed normally

## REMOVED Requirements

- **PO login returns the narrow `TokenResponse` model** — REMOVED. Replaced by `LoginResponse` with tier fields.
- **`_login_client_leadership` skips cross-tenant check** — REMOVED. Cross-tenant check is now mandatory for all tiers.

## Cross-references

- Predecessor spec: `openspec/changes/add-c02-user-creation-activation/specs/authentication/spec.md`
- ADR: `docs/architecture/adr-c02-identity-user-management-implementation.md` (D6, D9, D10)
- Audit: `docs/architecture/audit-c02-implementation-2026-08-03.md`
