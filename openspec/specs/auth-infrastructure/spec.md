# auth-infrastructure Specification

## Purpose
TBD - created by archiving change add-c02-user-creation-activation. Update Purpose after archive.
## Requirements
### Requirement: update_user accepts user_metadata parameter

`SupabaseAuthClientImpl.update_user()` (the concrete implementation at `supabase_client.py` line ~253) SHALL accept `user_metadata: dict | None = None` as a keyword-only parameter. The method body already references `user_metadata` at line ~270–271 (`if user_metadata is not None: update_data["user_metadata"] = user_metadata`); adding the parameter to the signature resolves the `NameError`. The abstract base class `SupabaseAuthClient` already declares this parameter in its interface. Per D5.

#### Scenario: update_user called with user_metadata does not raise NameError
- **GIVEN** any caller invokes `await supabase.update_user(user_id, password="...", user_metadata={"user_tier": "institution"})`
- **WHEN** the method executes
- **THEN** `user_metadata` SHALL be included in the `update_data` dict sent to Supabase
- **AND** no `NameError` SHALL be raised

#### Scenario: update_user called without user_metadata still works
- **GIVEN** a caller invokes `await supabase.update_user(user_id, password="...", email_confirm=True)` without `user_metadata`
- **WHEN** the method executes
- **THEN** the `if user_metadata is not None:` branch SHALL be skipped
- **AND** the call SHALL succeed as before

#### Scenario: Existing callers verified
- **WHEN** the codebase is searched for all callers of `update_user()`
- **THEN** no caller SHALL break due to the added parameter (it is optional with a default of `None`)
- **AND** the bootstrap_invite path that previously triggered the NameError SHALL now work correctly

---

### Requirement: RLS session variables set on endpoint sessions

Every database session used by endpoint dependencies SHALL have the following PostgreSQL session variables set via `SET LOCAL`:
- `app.is_platform_owner` — `'true'` or `'false'` resolved from `TenantContext`
- `app.current_client_id` — the client UUID as a string, or NULL if not in a client context
- `app.current_user_id` — the authenticated user's UUID as a string, or NULL if unauthenticated

These SHALL be set after `TenantContext` is resolved (in middleware or a session-event hook) and before any endpoint handler runs. The setting SHALL be scoped to the transaction (`SET LOCAL`) so it does not leak across requests. Per D5.

#### Scenario: RLS vars set on authenticated request
- **GIVEN** an authenticated request with a valid JWT from a Client Director
- **WHEN** the middleware resolves `TenantContext` with `user_id`, `client_id`, and `is_platform_owner = False`
- **THEN** before the endpoint handler executes, the session SHALL have `SET LOCAL app.is_platform_owner = 'false'`
- **AND** `SET LOCAL app.current_client_id = '<client_uuid>'`
- **AND** `SET LOCAL app.current_user_id = '<user_uuid>'`

#### Scenario: RLS vars on unauthenticated activate request
- **GIVEN** an unauthenticated `POST /api/auth/activate` request
- **WHEN** the middleware resolves `TenantContext` with `user_id = None` and no client context
- **THEN** `SET LOCAL app.current_user_id` SHALL be NULL
- **AND** `app.current_client_id` SHALL be NULL
- **AND** the activate endpoint SHALL still function (operating with elevated privileges or RLS bypass for the auth path)

#### Scenario: Platform Owner request sets is_platform_owner
- **GIVEN** the Platform Owner authenticates at the platform URL
- **WHEN** the middleware resolves the tenant context
- **THEN** `SET LOCAL app.is_platform_owner = 'true'`
- **AND** RLS policies that check `is_platform_owner` SHALL grant access accordingly

#### Scenario: SET LOCAL scope does not leak across requests
- **GIVEN** request A sets `app.current_client_id = 'abc'`
- **WHEN** request B (a different request) begins a new session
- **THEN** `app.current_client_id` SHALL NOT be `'abc'` — it SHALL be whatever request B's context resolves to
- **AND** no cross-request session variable leakage SHALL occur

---

### Requirement: conftest.py RLS bypass updated for new plumbing

The test infrastructure at `tests/conftest.py` line 142 (which currently sets `SET LOCAL app.is_platform_owner = 'true'` on every test session) SHALL be updated to match the production session-var plumbing. Tests that require specific RLS context SHALL explicitly set the session variables they need, rather than relying on a blanket platform-owner bypass that masks production gaps. Per D5.

#### Scenario: Tests no longer mask the RLS gap
- **WHEN** the test suite runs after the session-var hook is implemented
- **THEN** tests SHALL NOT rely on `conftest.py` line 142 to set RLS variables globally
- **AND** each test SHALL set only the RLS context it needs (e.g., platform owner, client director, institution user)
- **AND** the test suite SHALL pass (no regressions)

