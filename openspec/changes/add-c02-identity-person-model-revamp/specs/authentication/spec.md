# Delta Spec — Authentication (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** authentication
> **Delta type:** MODIFIED
> **Base spec:** `openspec/specs/authentication/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a, D3d, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-19, AC-21)

---

## MODIFIED Requirements

### REQ-AUTH-01: Unified Activation for Both User Tiers (Modified — person linkage)

`POST /api/auth/activate` SHALL handle both `client_user` and `app_user` tables. It SHALL first look up the user by UUID in `app_user`, and if not found, fall back to `client_user`. The lookup SHALL use `session.get()` (by primary key) for both tables, bypassing tenant filters. The underlying account row now carries `person_id` linking to `person`; the activate behavior (verify invite JWT, set password, transition `invited → active`) is unchanged. The response shape `{message, user_id, user_tier, client_slug}` is preserved. Per D1, AC-19, AC-21.

#### Scenario: Activate resolves institution user in app_user (unchanged behavior)
- **GIVEN** a valid invite JWT with `sub` pointing to an `app_user` row in `invited` state
- **WHEN** `POST /api/auth/activate` is called with `{invite_token, password}`
- **THEN** the user SHALL be found in `app_user`
- **AND** the `app_user` row SHALL link to a `person` via `person_id`
- **AND** the lifecycle SHALL transition `invited → active`
- **AND** the response SHALL include `user_tier: "institution"`

#### Scenario: Activate resolves Client Director in client_user (unchanged behavior)
- **GIVEN** a valid invite JWT with `sub` pointing to a `client_user` row in `invited` state
- **WHEN** `POST /api/auth/activate` is called with `{invite_token, password}`
- **THEN** the user SHALL be found in `client_user`
- **AND** the `client_user` row SHALL link to a `person` via `person_id`
- **AND** the lifecycle SHALL transition `invited → active`
- **AND** the response SHALL include `user_tier: "client_leadership"`

#### Scenario: Activate returns 404 when user not found (unchanged)
- **GIVEN** a valid invite JWT but the user_id does not exist in `app_user` or `client_user`
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `404 User not found`

---

### REQ-AUTH-02: Activate Response Shape (Modified — unchanged, person linkage noted)

The response from `POST /api/auth/activate` SHALL be `{message, user_id, user_tier, client_slug}`. It SHALL NOT return `access_token` or `refresh_token`. The `client_slug` derivation and `user_tier` stamping are unchanged. The response is **unchanged in shape** — the `person_id` is not added to the activate response (the user does not need it at activation; they get it from the JWT on subsequent login). Per D4, AC-21.

#### Scenario: Activate response for institution user (unchanged)
- **GIVEN** an institution user activating via `/api/auth/activate`
- **WHEN** activation succeeds
- **THEN** the response SHALL be `{message: "User activated successfully", user_id: "<uuid>", user_tier: "institution", client_slug: "<slug>"}`
- **AND** SHALL NOT contain `access_token`, `refresh_token`, or `token`

#### Scenario: Activate response for Client Director (unchanged)
- **GIVEN** a CD activating via `/api/auth/activate`
- **WHEN** activation succeeds
- **THEN** the response SHALL be `{message: "User activated successfully", user_id: "<uuid>", user_tier: "client_leadership", client_slug: "<slug>"}`
- **AND** SHALL NOT contain `access_token`, `refresh_token`, or `token`

---

### REQ-AUTH-03: Password Validation on Activate (Modified — no structural change)

Password validation on activate delegates to Supabase Auth via `update_user(password=..., email_confirm=True)`. This flow operates on the Supabase Auth user, not on `app_user`/`client_user` human columns. Since human data has moved to `person` and the account tables no longer carry human columns, these flows are **unaffected structurally**. Behavior is unchanged. Per D1, AC-19.

#### Scenario: Weak password rejected (unchanged)
- **GIVEN** a valid invite JWT
- **WHEN** `POST /api/auth/activate` is called with password `"123"`
- **THEN** Supabase Auth SHALL reject it
- **AND** the endpoint SHALL return `400 Bad Request` (or `502 Bad Gateway`)
- **AND** the user's lifecycle SHALL remain `invited`

#### Scenario: Already-active user returns 400 (unchanged)
- **GIVEN** a valid invite JWT for a user whose lifecycle is already `active`
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `400 User is already active`

#### Scenario: Invalid or expired invite token returns 400 (unchanged)
- **GIVEN** an invite JWT that is expired or has been tampered with
- **WHEN** `POST /api/auth/activate` is called
- **THEN** the response SHALL be `400 Invalid invite token`

---

### REQ-AUTH-04: Token Claims — person_id (Modified-pending-design)

The institution JWT currently carries tenant + roles claims; the CD JWT carries `{sub, user_tier, client_id, role_id, exp}`. Whether `person_id` is added to JWT claims is a **design-phase decision** — it is listed as an impact area but not mandated by an acceptance criterion. The authz pipeline requires NO per-request `person` joins (D3d, D8); roles stay on the account. Per D3d, D8, AC-17, AC-18.

> **Design decision (deferred to design.md):** whether to add `person_id` to JWT claims for convenience (cross-institution reporting, person-keyed queries) or keep the JWT account-scoped. The authz pipeline is unaffected either way.

#### Scenario: Authz pipeline unchanged regardless of person_id in claims
- **WHEN** the Casbin middleware processes an authenticated request
- **THEN** it SHALL read roles from the account (via `role_assignment` / `client_user.role_id`)
- **AND** SHALL NOT perform per-request `person` joins for authorization
- **AND** the authz behavior SHALL be byte-for-byte unchanged (AC-17, AC-18)

---

## Account-Parent Model (Resolved — D3f: person and user_account coexist)

> **Q8 RESOLVED as D3f:** `person` and `user_account` coexist. `login_attempt.user_id` SHALL target `user_account.id` (unchanged). See `identity-user-management` delta spec §Creation Flow for the full resolution.

### REQ-AUTH-Q8-01: login_attempt.user_id FK Target (Resolved — D3f)

`login_attempt.user_id` SHALL target `user_account.id` (UNCHANGED). A credential (account) attempts login, not a human; the FK referent stays on the account parent. Per D3f, D12.

#### Scenario: login_attempt targets user_account (unchanged)
- **WHEN** a `login_attempt` row is inspected
- **THEN** `login_attempt.user_id` SHALL reference `user_account.id`
- **AND** SHALL NOT reference `person.id`
- **AND** login-audit requirements that depend on the referent SHALL remain unchanged
