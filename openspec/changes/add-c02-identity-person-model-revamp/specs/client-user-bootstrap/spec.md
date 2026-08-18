# Delta Spec — Client User Bootstrap (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** client-user-bootstrap
> **Delta type:** MODIFIED + REMOVED
> **Base spec:** `openspec/specs/client-user-bootstrap/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3e, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-7, AC-8, AC-11, AC-20)

---

## MODIFIED Requirements

### REQ-CUB-01: Two-Tier User Model (Modified — client_user thinned, person linkage)

The platform SHALL model users in two physically distinct tables: `client_user` for client-leadership-scope users and `app_user` for institution-scoped users. `client_user` SHALL be a **thin account** carrying auth + `person_id` (nullable FK → `person.id`) + client scope (`client_id`) + lifecycle — no human data. Human data (name, DOB, contact, demographics) SHALL live on the linked `person`. No row in `client_user` SHALL have an `institution_id` column. `app_user.institution_id` SHALL remain NOT NULL. Per D3e, D6a, AC-7, AC-8.

#### Scenario: Physically distinct tables with person linkage
- **WHEN** the database schema is inspected
- **THEN** `client_user` SHALL exist with `client_id`, `person_id`, `role_id`, and NO `institution_id` column
- **AND** `app_user` SHALL have `institution_id` declared NOT NULL and `person_id` → `person.id`
- **AND** both tables SHALL link to `person` via `person_id`

#### Scenario: Client-leadership user lives in client_user with person
- **WHEN** a Client Director is created
- **THEN** the row SHALL be inserted into `client_user` with `person_id` → a `person` row
- **AND** the `person` row SHALL own the human data (name, etc.)
- **AND** the `client_user` row SHALL NOT carry human data columns

---

### REQ-CUB-02: client_user Table Structure (Modified — thinned)

The `client_user` table SHALL carry: `id`, `email`, `person_id` (nullable FK → `person.id`), `lifecycle_status`, `role_id` (UUID FK → `role`), `client_id` (UUID FK → `client`), `created_at`, `updated_at`. The `name` column SHALL be removed (human name lives on `person`). The `user_category_id` column SHALL be removed. The table SHALL NOT include `institution_id`. The `role_id` column SHALL store the single client-leadership role directly (no separate `client_role_assignment` table). Per D3e, D6a, AC-7, AC-11.

#### Scenario: Column set after thinning
- **WHEN** the `client_user` table is created
- **THEN** it SHALL include `id`, `email`, `person_id`, `lifecycle_status`, `role_id`, `client_id`, `created_at`, `updated_at`
- **AND** it SHALL NOT include `name`, `user_category_id`, or `institution_id`

#### Scenario: Role FK target (unchanged)
- **WHEN** a `client_user.role_id` value is inspected
- **THEN** it SHALL reference an existing row in the global `role` table
- **AND** the referenced role SHALL be a client-leadership role

---

### REQ-CUB-03: Login Lookup by user_metadata.user_tier (Modified — person linkage, behavior preserved)

The `/api/auth/login` flow SHALL read `user_metadata.user_tier` and branch to the correct table lookup. Behavior is preserved (CD→`client_user`, institution→`app_user`); both tables now link to `person`. The `user_tier` stamping at creation is unchanged. Per D2, AC-19.

#### Scenario: Client-leadership login resolves to client_user (unchanged behavior)
- **WHEN** a Supabase Auth user with `user_metadata.user_tier = "client_leadership"` submits login credentials
- **THEN** the login flow SHALL look up the user in `client_user`
- **AND** the `client_user` row SHALL link to a `person` via `person_id`

#### Scenario: Institution login resolves to app_user (unchanged behavior)
- **WHEN** a Supabase Auth user with `user_metadata.user_tier = "institution"` submits login credentials
- **THEN** the login flow SHALL look up the user in `app_user`
- **AND** the `app_user` row SHALL link to a `person` via `person_id`

#### Scenario: user_tier stamped at user creation (unchanged)
- **WHEN** the PO bootstrap endpoint creates a CD
- **THEN** the new Auth user's `user_metadata.user_tier` SHALL be set to `"client_leadership"`
- **AND** when the CD creates an institution user, `user_metadata.user_tier` SHALL be set to `"institution"`

---

### REQ-CUB-04: CD Own-Row Access — Display Name Update via Person (Modified)

A CD SHALL be able to SELECT and UPDATE only their own row in `client_user`. The display-name update SHALL route through the `person` link: the `name` field now lives on `person`, so `PATCH .../$SELF_ID` with a name change SHALL update the linked `person.name`, not a `client_user.name` column (which no longer exists). RLS on `client_user` (own-row) is unchanged in shape. Per D5, D6a, AC-7.

#### Scenario: CD updates own display name via person
- **WHEN** a CD calls `PATCH /api/v1/platform/clients/$ID/users/$SELF_ID` with `{name: "New Display Name"}`
- **THEN** the update SHALL set `person.name` on the `person` linked to the CD's `client_user.person_id`
- **AND** the `client_user` row SHALL be updated only for non-human fields (if any)

#### Scenario: CD reads own row (unchanged RLS)
- **WHEN** a CD calls `GET /api/v1/platform/clients/$ID/users/$SELF_ID`
- **THEN** the response SHALL return the CD's own row with `person` projection
- **AND** RLS SHALL filter through `id = current_user_id()`

#### Scenario: CD cannot read sibling CD (unchanged)
- **WHEN** a CD calls `GET /api/v1/platform/clients/$ID/users/$SIBLING_ID`
- **THEN** the response SHALL be `404` (RLS filtered the row out)

---

### REQ-CUB-05: Bootstrap Creates an Invited CD with Person (Modified)

The bootstrap endpoint SHALL create the CD's Supabase Auth user in the `invited` state with NO password. The endpoint SHALL also create/link a `person` row carrying the human data (name, etc.) and create the `client_user` row with `person_id` → the `person.id`. The request body SHALL include `person_data` (human data) instead of a flat `name` field. Per D6, D3a, D6a, AC-20.

#### Scenario: No password in request (unchanged)
- **WHEN** the PO calls bootstrap with a request body containing a `password` field
- **THEN** the request SHALL be rejected with `400 unexpected field password`

#### Scenario: Bootstrap creates person and client_user
- **WHEN** the PO calls bootstrap with `{email, person_data: {name, …}, role}`
- **THEN** a `person` row SHALL be created with the human data
- **AND** a `client_user` row SHALL be created with `person_id` → the new `person.id`
- **AND** the Supabase Auth user SHALL have no password and `lifecycle_status = "invited"`

---

### REQ-CUB-06: Casbin Policy Loader — Dual Source (Modified — referent Q8-dependent)

The Casbin policy loader SHALL read `role_assignment` (institution roles) and `client_user.role_id` (client-leadership roles). The `role_assignment.user_id` FK SHALL target `user_account.id` (unchanged — roles are account-scoped per D8 + D3b; `person` and `user_account` coexist per D3f). The loader behavior (startup + on-demand) is unchanged; the query text is unchanged. Per D3, D8, D3f.

#### Scenario: Loader reads both sources (unchanged behavior)
- **WHEN** the platform starts up
- **THEN** the Casbin enforcer SHALL be populated from `role_assignment` (institution roles) and `client_user.role_id` (client-leadership roles)
- **AND** load order SHALL be deterministic

#### Scenario: CD role resolved from JWT (unchanged)
- **WHEN** a CD makes a request with a `client_leadership` JWT carrying `role_id`
- **THEN** the middleware SHALL use the JWT's `role_id` claim directly
- **AND** SHALL NOT consult the Casbin enforcer per request

---

## REMOVED Requirements

### REQ-CUB-REM-01: user_category_id from client_user

The `user_category_id` column SHALL be removed from `client_user`. All requirements and logic keyed on `client_user.user_category_id` SHALL be removed. Per D6a, AC-11.

#### Scenario: user_category_id gone from client_user
- **WHEN** the `client_user` table schema is inspected
- **THEN** there SHALL be no `user_category_id` column
- **AND** no client_user creation, list, or filter logic SHALL reference `user_category_id`

---

## Creation Flow and Account-Parent Model (Resolved — D3f: person and user_account coexist)

> **Q8 RESOLVED as D3f:** `person` and `user_account` coexist. `user_account` is the account parent (FK target for `role_assignment`/`login_attempt`); `person` is the human anchor. `person.id` is independent of the account UUID. See `identity-user-management` delta spec §Creation Flow for the full resolution.

### REQ-CUB-Q8-01: client_user Creation Insert Order (Resolved — D3f)

The CD bootstrap creation flow SHALL insert in this order: (1) `person` (independent UUID, human data), (2) `user_account` (D12 shared-UUID parent), (3) `client_user` carrying the `user_account` UUID, (4) set `client_user.person_id` → the `person.id`. The `user_account`-first invariant from D12 is preserved for the account-parent insert; `person` is inserted before it. Per D3f, D12, D3a, AC-20.

#### Scenario: CD bootstrap creation insert order
- **GIVEN** the Platform Owner bootstraps a CD
- **WHEN** the creation transaction executes
- **THEN** `person` SHALL be inserted first (independent UUID, human data)
- **AND** `user_account` SHALL be inserted second (shared-UUID parent per D12)
- **AND** `client_user` SHALL be inserted third carrying the `user_account` UUID
- **AND** `client_user.person_id` SHALL be set → the `person.id`

#### Scenario: person.id is independent of account UUID
- **GIVEN** a CD's person and account are created
- **WHEN** the UUIDs are compared
- **THEN** `person.id` SHALL NOT equal the account UUID
- **AND** the account UUID is the `user_account.id` (D12 pattern, preserved)
