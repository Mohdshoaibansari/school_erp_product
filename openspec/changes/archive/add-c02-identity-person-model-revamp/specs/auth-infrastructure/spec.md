# Delta Spec — Auth Infrastructure (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** auth-infrastructure
> **Delta type:** MODIFIED (conditional / Q8-dependent)
> **Base spec:** `openspec/specs/auth-infrastructure/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-17)

---

## MODIFIED Requirements (conditional)

### REQ-AUTHINF-01: RLS Session Variables — current_user_id Referent (Modified — Q8-conditional)

The RLS session variables (`app.is_platform_owner`, `app.current_client_id`, `app.current_user_id`) SHALL continue to be set via `SET LOCAL` on every endpoint session. `app.current_user_id` SHALL map to the authenticated user's UUID. Whether this UUID is the account id (`app_user.id`/`client_user.id`) or the `person.id` depends on **Q8**. The `update_user` accepts `user_metadata` requirement is unchanged (the activate flow still stamps `user_tier`). Per D5, AC-17.

#### Scenario: RLS vars set on authenticated request (unchanged behavior)
- **GIVEN** an authenticated request with a valid JWT
- **WHEN** the middleware resolves `TenantContext`
- **THEN** `SET LOCAL app.is_platform_owner`, `app.current_client_id`, `app.current_user_id` SHALL be set before the endpoint handler runs
- **AND** `SET LOCAL` scope SHALL NOT leak across requests

#### Scenario: update_user with user_metadata (unchanged)
- **GIVEN** a caller invokes `await supabase.update_user(user_id, password="...", user_metadata={"user_tier": "institution"})`
- **WHEN** the method executes
- **THEN** `user_metadata` SHALL be included in the `update_data` dict
- **AND** no `NameError` SHALL be raised

---

## Account-Parent Model (Resolved — D3f: person and user_account coexist)

> **Q8 RESOLVED as D3f:** `person` and `user_account` coexist. `app.current_user_id` SHALL continue to mean the acting account's `user_account.id` (UNCHANGED). RLS policies keyed on `current_user_id` do NOT reinterpret to `person.id`. **No delta is required to this domain** beyond the note above. See `identity-user-management` delta spec §Creation Flow for the full resolution.

### REQ-AUTHINF-Q8-01: app.current_user_id Referent (Resolved — D3f, no change needed)

`app.current_user_id` SHALL continue to map to the acting account's `user_account.id` (UNCHANGED). RLS policies keyed on `current_user_id` do NOT reinterpret to `person.id`; `person` is not an RLS scoping dimension. The `update_user` accepts `user_metadata` requirement is unchanged. No further delta is needed in this domain. Per D3f, D5, AC-17.

#### Scenario: current_user_id referent unchanged (confirmed)
- **WHEN** the RLS session variable `app.current_user_id` is set
- **THEN** it SHALL map to the acting account's `user_account.id`
- **AND** SHALL NOT map to `person.id`
- **AND** RLS policies on account tables (`app_user`, `client_user`) SHALL filter by `user_account.id` (unchanged)
