# identity-user-management Specification

## Purpose
TBD - created by archiving change add-c02-user-creation-activation. Update Purpose after archive.
## Requirements
### Requirement: Unified invite token minting for institution users

`POST /api/v1/users` SHALL mint an invite JWT for every newly created institution user and return it alongside the user record. The response contract SHALL be `{user: UserDTO, invite_url: str}`. The invite JWT SHALL be minted using the existing `mint_invite_token()` function from `kernel/auth/services/invite_token.py` with the user's UUID and email. Per D1.

#### Scenario: Institution user creation returns invite_url
- **GIVEN** a Client Director is authenticated with a valid `client_id` and `institution_id`
- **WHEN** `POST /api/v1/users` is called with `{email, name, user_category_id, institution_id}`
- **THEN** the response SHALL contain `user` (a full `UserDTO` as currently returned) AND `invite_url` (a string containing the invite JWT)
- **AND** the Supabase Auth user SHALL be created with no password
- **AND** the `app_user` row SHALL have `lifecycle_status = "invited"`

#### Scenario: Invite JWT is valid and verifiable
- **GIVEN** the invite_url returned from user creation
- **WHEN** the token is extracted and verified via `verify_invite_token()`
- **THEN** the decoded payload SHALL contain `sub` (the user's UUID) and `email`
- **AND** the `iss` claim SHALL be `"school-erp/invite"`
- **AND** the `exp` claim SHALL be `now + config.get('auth.inviteExpiryDays')` days

#### Scenario: PO-created Client Director already returns invite_url (no regression)
- **GIVEN** the Platform Owner bootstrap endpoint `POST /api/v1/platform/clients/{id}/users`
- **WHEN** called with CD details
- **THEN** the response SHALL continue to include `invite_url` as before
- **AND** the invite JWT SHALL be structurally identical to institution-user invite JWTs

---

### Requirement: Optional role_id on user creation

`POST /api/v1/users` SHALL accept an optional `role_id` field in the request body. When provided, the role SHALL be assigned atomically in the same database transaction as user creation by inserting a row into the `role_assignment` table (or its equivalent). When omitted, the user SHALL be created without a role assignment — role assignment can be performed later via `POST /api/v1/users/{id}/roles`. Per D2.

#### Scenario: User created with role_id
- **GIVEN** a valid `role_id` for a role available in the current institution
- **WHEN** `POST /api/v1/users` is called with `{email, name, user_category_id, institution_id, role_id}`
- **THEN** the response SHALL contain the created user AND `invite_url`
- **AND** a `role_assignment` row SHALL exist linking the user to the role in the specified institution
- **AND** the role assignment SHALL be committed in the same transaction as the `app_user` row

#### Scenario: User created without role_id
- **GIVEN** a request body that does NOT include `role_id`
- **WHEN** `POST /api/v1/users` is called
- **THEN** the user SHALL be created successfully with `lifecycle_status = "invited"`
- **AND** no `role_assignment` row SHALL exist for this user
- **AND** the existing `POST /api/v1/users/{id}/roles` endpoint SHALL still be available for later assignment

#### Scenario: Invalid role_id returns 400
- **GIVEN** a `role_id` that does not exist or is not available at this institution
- **WHEN** `POST /api/v1/users` is called
- **THEN** the response SHALL be `400 Bad Request` with a message indicating the role is invalid
- **AND** no user SHALL be created (atomic rollback)

---

### Requirement: Single lifecycle arc for all user types

Both `client_user` and `app_user` rows SHALL follow the lifecycle `invited → active` via `/api/auth/activate`. The `pending` state SHALL be retained on the lifecycle state machine for manual admin transitions via `POST /api/v1/users/{id}/transition` but SHALL NOT be used in the normal activation flow. Per D1.

#### Scenario: Institution user transitions invited → active via activate
- **GIVEN** an institution user in `invited` state
- **WHEN** the user completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `app_user.lifecycle_status` SHALL be `"active"`
- **AND** a `user_lifecycle_event` row SHALL record the transition with reason `"Completed invite activation"`

#### Scenario: Client Director transitions invited → active via activate (no regression)
- **GIVEN** a CD in `invited` state
- **WHEN** the CD completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `client_user.lifecycle_status` SHALL be `"active"`
- **AND** a `client_user_lifecycle_event` row SHALL record the transition

#### Scenario: pending state preserved on state machine
- **GIVEN** the user lifecycle state machine definition
- **WHEN** inspected
- **THEN** `pending` SHALL remain a valid state
- **AND** `POST /api/v1/users/{id}/transition` SHALL still support `invited → pending` and `pending → active` transitions

---

### Requirement: Config-driven invite URL

The invite URL returned by both `POST /api/v1/users` (institution users) and `POST /api/v1/platform/clients/{id}/users` (CDs) SHALL be built using the config key `app.activationBaseUrl`. The URL format SHALL be `{app.activationBaseUrl}/activate?token={invite_jwt}`. The hardcoded `"http://127.0.0.1:8000"` SHALL be removed from `client_user_service.py`. Per D3.

#### Scenario: Invite URL uses config value
- **GIVEN** `app.activationBaseUrl` is set to `"https://app.school-erp.com"`
- **WHEN** any user creation endpoint mints an invite URL
- **THEN** the URL SHALL be `"https://app.school-erp.com/activate?token=<jwt>"`
- **AND** SHALL NOT be `"http://127.0.0.1:8000/activate?token=<jwt>"`

#### Scenario: Dev default when config not explicitly set
- **GIVEN** `app.activationBaseUrl` has its seeded default value
- **WHEN** the invite URL is built in a local dev environment
- **THEN** the URL SHALL default to a value suitable for local development (e.g., `"http://127.0.0.1:8000"`)


---

## ADDED Requirements (from add-c05-academic-structure)

- `teacher_assignment.teacher_id` → FK to `app_user.id`
- `section.homeroom_teacher_id` → FK to `app_user.id`

**Rules:**
- Teacher must exist in `app_user` table
- Teacher must have "Teacher" role (validated in service layer)
- No schema changes to C-02 tables — FK is on C-05 side

---

### REQ-USER-AC-02: Student Enrollment Reference

C-05 `StudentEnrollment` references `app_user.id` for student enrollment.

**Fields affected:**
- `student_enrollment.student_id` → FK to `app_user.id`

**Rules:**
- Student must exist in `app_user` table
- Student must have "Student" role (validated in service layer)
- No schema changes to C-02 tables — FK is on C-05 side

---

### REQ-FE-USR-01: Users List/Create/Edit/Transition

The app SHALL provide a Users screen (scoped to the user's client/institution) where the Client Director or Institution Admin can list, create (category, identifiers, contact), edit, and transition the status (activate/suspend/deactivate) of users, and open a user's profile (P1-AC-19).

#### Scenario: Manage users scoped to tenant
- **WHEN** a Client Director or Institution Admin acts on the Users screen
- **THEN** they can list, create, edit, and transition users within their client/institution scope, and open a user's profile

---

### REQ-FE-USR-02: Profile View and Edit

The app SHALL provide a user profile view where profile fields can be edited (CRUD on profile fields) (P1-AC-20).

#### Scenario: Edit profile fields
- **WHEN** a user opens another user's profile
- **THEN** they can view and edit the profile fields

---

### REQ-FE-USR-03: Identifier Management

The app SHALL provide identifier management on a user's profile: list, create, edit, and remove identifiers (P1-AC-21).

#### Scenario: Manage identifiers
- **WHEN** a user opens a profile's identifiers
- **THEN** they can list, create, edit, and remove identifiers

---

### REQ-FE-USR-04: Role Assignment

The app SHALL provide a roles view on a user's profile where roles can be viewed, assigned, and removed from the available role catalog (P1-AC-22).

#### Scenario: Assign and remove roles
- **WHEN** a user opens a profile's roles
- **THEN** they can view current roles and assign/remove roles from the available role catalog

---

### REQ-FE-USR-05: Lookups-Driven Reference Dropdowns

Reference dropdowns on user forms (user-category, role, institution-type, org-unit-type, legal-entity-type) SHALL be populated from the lookups API as the single source of truth for reference data (P1-AC-23).

#### Scenario: Dropdowns sourced from lookups API
- **WHEN** a user form renders a reference dropdown
- **THEN** its values are populated from the lookups API

---

### REQ-FE-USR-06: No Roles & Permissions Screen

The app SHALL NOT provide a Roles & Permissions screen in this build because C-04 exposes no HTTP routes. Role-based gating is derived from the JWT `roles` claim, and the backend enforces Casbin (P1-AC-24, R1).

#### Scenario: No roles/permissions management screen
- **WHEN** a user inspects available navigation
- **THEN** there is no Roles & Permissions screen; navigation and actions are role-gated from the JWT `roles` claim

---

# Delta Spec — Identity & User Management (Person-Model Revamp)

> **Change:** `add-c02-identity-person-model-revamp`
> **Domain:** identity-user-management
> **Delta type:** ADDED + MODIFIED + REMOVED
> **Base spec:** `openspec/specs/identity-user-management/spec.md`
> **Source ADR:** `docs/architecture/adr-c02-identity-person-model-revamp.md` (D3a–D3e, D6a)
> **Source PRD:** `docs/prd/c02-identity-person-model-revamp.md` (AC-1..AC-26)

---

## ADDED Requirements

### REQ-IUM-PERSON-01: Person Entity as Enduring-Human Anchor

A `person` entity SHALL exist as the enduring-human anchor of the identity model. One human = one `person` row. `person` SHALL own all human-intrinsic attributes: `name`, `dob`, `gender`, `blood_group`, `photo`, contact, and demographics. `person` SHALL have a primary key `id` (UUID). No human-intrinsic attribute (name, DOB, contact, demographics) SHALL live on any account table (`app_user` or `client_user`). Per D3a, D6a, AC-1.

#### Scenario: Person owns human data
- **GIVEN** a human exists on the platform
- **WHEN** the `person` row is inspected
- **THEN** it SHALL contain `name`, `dob`, `gender`, `blood_group`, `photo`, contact, and demographics fields
- **AND** no account table (`app_user`, `client_user`) SHALL carry any of these human-intrinsic columns

#### Scenario: One person per human
- **GIVEN** a human who is both a teacher and a future parent
- **WHEN** the human's projections are resolved
- **THEN** all projections SHALL resolve to a single `person` row
- **AND** the `person` row SHALL be the enduring anchor across lifecycle transitions (student→alumni→employee)

#### Scenario: Person may exist with zero accounts
- **GIVEN** an admin creates a `person` for a pre-login student record
- **WHEN** the person is inspected for linked accounts
- **THEN** the person SHALL exist with no `app_user` and no `client_user` row
- **AND** the person's human data is fully present

---

### REQ-IUM-PERSON-02: Person Orthogonal Status Classifier

`person` SHALL carry an orthogonal status classifier: `Active | Inactive | Deceased | ErasureRequested | Anonymized`. This status is the *existence/retention* classifier, set by external processes (GDPR, registrar, verification) — it is NOT a behavioral lifecycle and SHALL NOT compete with student/employee behavioral lifecycles (which are owned by domain entities in the next capability). Default status SHALL be `Active`. Per D3c, AC-2.

#### Scenario: Default status is Active
- **GIVEN** a new `person` is created
- **WHEN** the row is inspected
- **THEN** `person.status` SHALL be `Active`

#### Scenario: Status set by external process
- **GIVEN** a registrar marks a person `Deceased`
- **WHEN** the person's status is updated
- **THEN** `person.status` SHALL become `Deceased`
- **AND** student/employee behavioral lifecycles (if any exist) SHALL remain independent and unchanged

#### Scenario: Status is not a behavioral lifecycle
- **GIVEN** a student transitions from Enrolled to Graduated
- **WHEN** the transition completes
- **THEN** `person.status` SHALL NOT automatically change
- **AND** only an external process (GDPR, registrar) may set `person.status`

---

### REQ-IUM-PERSON-03: Person is Role-Agnostic

`person` SHALL carry no role, classification, or `person_type` field. "What can this human do" is answered by account + institution + `role_assignment` (D8) + the `is_platform_owner` flag. Human-intrinsic facts (minor, verified) are non-role attributes on `person` or derived from projections. The system SHALL NOT reintroduce a singular human classification. Per D3d, AC-3.

#### Scenario: No person-level role field
- **WHEN** the `person` table schema is inspected
- **THEN** there SHALL be no `role_id`, `user_category_id`, `person_type`, or classification column
- **AND** capabilities SHALL be derived from account-scoped `role_assignment` rows

#### Scenario: Multi-projection person has no singular type
- **GIVEN** a person who is both a historical student and a current employee
- **WHEN** the person's capabilities are resolved
- **THEN** the system SHALL resolve capabilities from the active account's `role_assignment`
- **AND** SHALL NOT consult any person-level classification

---

### REQ-IUM-PERSON-04: Multiple Accounts Per Person; One Institution Per Account

A `person` MAY have zero, one, or many `app_user` accounts. Each `app_user` account SHALL have exactly one `institution_id` (NOT NULL, singular). A cross-institution human = one `person`, multiple `app_user` rows (one per institution), each with its own `role_assignment`. Cross-institution *reporting* works via `person` joins; cross-institution *login* is per-account (no SSO across institutions). Per D3b, AC-4, AC-5.

#### Scenario: Person with multiple institution accounts
- **GIVEN** a teacher works at School A1 and School A2 (same client)
- **WHEN** the teacher's accounts are listed
- **THEN** there SHALL be one `person` row and two `app_user` rows (one per institution)
- **AND** each `app_user` SHALL have a distinct `institution_id` (NOT NULL) and its own `role_assignment`

#### Scenario: Cross-institution reporting via person
- **GIVEN** a person with accounts at two institutions
- **WHEN** a cross-institution report queries "all of this person's classes"
- **THEN** the query SHALL join through `person.id` and return results spanning both institutions

#### Scenario: No cross-institution SSO
- **GIVEN** a person with accounts at two institutions
- **WHEN** the person logs in
- **THEN** they SHALL log in per-account (one login per institution)
- **AND** there SHALL be no single-sign-on across institutions in this revamp

---

### REQ-IUM-PERSON-05: Account-to-Person Link

`app_user.person_id` SHALL be a nullable FK → `person.id`. `client_user.person_id` SHALL be a nullable FK → `person.id`. The link is nullable because a `person` may have no account. Both account tables (`app_user`, `client_user`) link to `person` — three account tiers: platform (`is_platform_owner` flag), client (`client_user`), institution (`app_user`). Per D3a, D3e, AC-8.

#### Scenario: app_user links to person
- **GIVEN** an institution user with a created account
- **WHEN** the `app_user` row is inspected
- **THEN** `app_user.person_id` SHALL reference an existing `person.id`
- **AND** the `person` row SHALL own the human data (name, DOB, etc.)

#### Scenario: client_user links to person
- **GIVEN** a Client Director with a created account
- **WHEN** the `client_user` row is inspected
- **THEN** `client_user.person_id` SHALL reference an existing `person.id`

#### Scenario: Person with no account
- **GIVEN** a `person` created for a pre-login student record
- **WHEN** linked accounts are queried
- **THEN** no `app_user` or `client_user` row SHALL reference this `person.id`
- **AND** the `person` row is fully valid

---

### REQ-IUM-PERSON-06: User Creation Creates/Links a Person

User creation (`POST /api/v1/users` for institution users, `POST /api/v1/platform/clients/{id}/users` for CDs) SHALL create or link a `person` row carrying the human data that previously lived on `app_user`/`user_profile`. The human data in the request body (name, and other human-intrinsic fields) SHALL be written to `person`, not to the account table. The account row SHALL be created with `person_id` linking to the `person`. Per D3a, D6a, AC-20.

#### Scenario: Institution user creation creates a person
- **GIVEN** a Client Director creates an institution user via `POST /api/v1/users`
- **WHEN** the request includes human data (name, etc.)
- **THEN** a `person` row SHALL be created with the human data
- **AND** an `app_user` row SHALL be created with `person_id` → the new `person.id`
- **AND** the `app_user` row SHALL carry only auth + tenant + lifecycle fields (no human data)

#### Scenario: CD bootstrap creates a person
- **GIVEN** the Platform Owner bootstraps a CD via `POST /api/v1/platform/clients/{id}/users`
- **WHEN** the request includes human data (name, etc.)
- **THEN** a `person` row SHALL be created with the human data
- **AND** a `client_user` row SHALL be created with `person_id` → the new `person.id`

---

### REQ-IUM-PERSON-07: Platform Owner Discovery via is_platform_owner Flag

Platform Owner discovery SHALL use the `is_platform_owner` flag/claim (already in the JWT), NOT `user_category`. No code SHALL discover platform owners by `user_category` after this revamp. Per D6a, AC-13.

#### Scenario: PO discovered by flag
- **WHEN** the system checks whether a user is a Platform Owner
- **THEN** it SHALL check the `is_platform_owner` flag/claim
- **AND** SHALL NOT consult any `user_category` value

---

### REQ-IUM-MIG-01: Coordinated Clean-Cut Migration

One coordinated clean-cut migration (schema + reseed) SHALL introduce `person`, add `person_id` to both account tables (`app_user`, `client_user`), drop `user_category_id` and `user_profile`, and set up domain-link repoints — in a single change. There SHALL be no backfill script and no adapter/dual-write phase. The disposable-DB assumption is scoped to this revamp only. Per D4, D5, AC-22, AC-23.

#### Scenario: Single coordinated migration
- **WHEN** the migration is applied to a disposable database
- **THEN** `person` table SHALL be created
- **AND** `app_user.person_id` and `client_user.person_id` SHALL be added (nullable FK → `person.id`)
- **AND** `app_user.user_category_id` SHALL be dropped
- **AND** `user_profile` table SHALL be dropped
- **AND** the database SHALL be reseeded (no backfill)

#### Scenario: No dual-write phase
- **WHEN** the migration strategy is reviewed
- **THEN** there SHALL be no adapter/dual-write phase
- **AND** the disposable-DB reseed is the sole data-population mechanism

---

## MODIFIED Requirements

### REQ-IUM-CREATE-01: Unified Invite Token Minting (Modified — person linkage)

`POST /api/v1/users` SHALL mint an invite JWT for every newly created institution user and return `{user: UserDTO, invite_url: str}`. The request body SHALL NOT include `user_category_id`. Human data (name, DOB, etc.) SHALL be provided as `person_data` and SHALL target the `person` entity; the `app_user` row SHALL be created with `person_id` linking to the person. The invite JWT, Supabase Auth user creation, and `lifecycle_status = "invited"` semantics are preserved from the base requirement. Per D1 (creation/activation ADR), D3a, D6a, AC-19, AC-20, AC-26.

#### Scenario: Institution user creation returns invite_url with person
- **GIVEN** a Client Director is authenticated with a valid `client_id` and `institution_id`
- **WHEN** `POST /api/v1/users` is called with `{email, person_data: {name, …}, institution_id, role_id?}`
- **THEN** the response SHALL contain `user` (a `UserDTO` with `person` projection) AND `invite_url`
- **AND** the Supabase Auth user SHALL be created with no password
- **AND** the `app_user` row SHALL have `lifecycle_status = "invited"` and `person_id` → the new `person.id`
- **AND** the request body SHALL NOT contain `user_category_id`

#### Scenario: Invite JWT is valid and verifiable (unchanged)
- **GIVEN** the invite_url returned from user creation
- **WHEN** the token is extracted and verified via `verify_invite_token()`
- **THEN** the decoded payload SHALL contain `sub` (the user's UUID) and `email`
- **AND** the `iss` claim SHALL be `"school-erp/invite"`
- **AND** the `exp` claim SHALL be `now + config.get('auth.inviteExpiryDays')` days

#### Scenario: PO-created Client Director already returns invite_url (no regression)
- **GIVEN** the Platform Owner bootstrap endpoint `POST /api/v1/platform/clients/{id}/users`
- **WHEN** called with CD details including `person_data`
- **THEN** the response SHALL continue to include `invite_url` as before
- **AND** the invite JWT SHALL be structurally identical to institution-user invite JWTs

---

### REQ-IUM-CREATE-02: Optional role_id on User Creation (Modified — person linkage)

`POST /api/v1/users` SHALL accept an optional `role_id` field. When provided, the role SHALL be assigned atomically in the same database transaction as user creation by inserting a `role_assignment` row. The `role_assignment.user_id` FK SHALL target `user_account.id` (unchanged — roles are account-scoped per D8 + D3b; `person` and `user_account` coexist as distinct entities per D3f). When `role_id` is omitted, the user SHALL be created without a role assignment. Per D2, D8, D3f, AC-19.

#### Scenario: User created with role_id
- **GIVEN** a valid `role_id` for a role available in the current institution
- **WHEN** `POST /api/v1/users` is called with `{email, person_data, institution_id, role_id}`
- **THEN** the response SHALL contain the created user AND `invite_url`
- **AND** a `role_assignment` row SHALL exist linking the user to the role in the specified institution
- **AND** the role assignment SHALL be committed in the same transaction as the `app_user` row

#### Scenario: User created without role_id
- **GIVEN** a request body that does NOT include `role_id`
- **WHEN** `POST /api/v1/users` is called
- **THEN** the user SHALL be created successfully with `lifecycle_status = "invited"`
- **AND** no `role_assignment` row SHALL exist for this user
- **AND** the existing `POST /api/v1/users/{id}/roles` endpoint SHALL still be available

#### Scenario: Invalid role_id returns 400
- **GIVEN** a `role_id` that does not exist or is not available at this institution
- **WHEN** `POST /api/v1/users` is called
- **THEN** the response SHALL be `400 Bad Request`
- **AND** no user SHALL be created (atomic rollback)

---

### REQ-IUM-LIFE-01: Single Lifecycle Arc for All User Types (Modified — person_id carrier)

Both `client_user` and `app_user` rows SHALL follow the lifecycle `invited → active` via `/api/auth/activate`. The `pending` state SHALL be retained on the state machine for manual admin transitions. The lifecycle arc is preserved in behavior; the underlying account row now carries `person_id` but the `invited → active` transition is unchanged. Per D1, AC-19.

#### Scenario: Institution user transitions invited → active via activate
- **GIVEN** an institution user in `invited` state
- **WHEN** the user completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `app_user.lifecycle_status` SHALL be `"active"`
- **AND** a `user_lifecycle_event` row SHALL record the transition with reason `"Completed invite activation"`

#### Scenario: Client Director transitions invited → active via activate (no regression)
- **GIVEN** a CD in `invited` state
- **WHEN** the CD completes `/api/auth/activate` with a valid invite token and password
- **THEN** the `client_user.lifecycle_status` SHALL be `"active"`
- **AND** a `client_user_lifecycle_event` row SHALL record the transition

#### Scenario: pending state preserved on state machine
- **GIVEN** the user lifecycle state machine definition
- **WHEN** inspected
- **THEN** `pending` SHALL remain a valid state
- **AND** `POST /api/v1/users/{id}/transition` SHALL still support `invited → pending` and `pending → active`

---

### REQ-IUM-ACCT-01: app_user Shape (Modified — thinned)

`app_user` SHALL be a thin account carrying only: auth fields (`sub`, `email`), `person_id` (nullable FK → `person.id`), tenant fields (`client_id`, `institution_id` — NOT NULL, singular per D3b), `lifecycle_status`, and last-login. `app_user` SHALL NOT carry any human-intrinsic data (name, DOB, gender, blood group, photo, contact, demographics). `app_user.user_category_id` SHALL NOT exist. Per D6a, AC-6, AC-9, AC-11.

#### Scenario: app_user is thin
- **WHEN** the `app_user` table schema is inspected
- **THEN** it SHALL contain `id`, `sub`, `email`, `person_id`, `client_id`, `institution_id` (NOT NULL), `lifecycle_status`, last-login, `created_at`, `updated_at`
- **AND** it SHALL NOT contain `name`, `dob`, `gender`, `blood_group`, `photo`, `user_category_id`, or any `user_profile` columns

#### Scenario: institution_id remains NOT NULL
- **WHEN** the `app_user.institution_id` column is inspected
- **THEN** it SHALL be declared NOT NULL (preserved per D3b)

---

### REQ-IUM-DTO-01: UserDTO Contract (Modified — person projection, breaking)

`UserDTO` SHALL include a `person` projection (`PersonDTO`: name, dob, gender, blood_group, photo, contact, demographics) sourced from the `person` entity. `UserDTO` SHALL NOT include `user_category_id` or any flat `user_profile` fields. This is a **breaking contract change** — all in-repo consumers (frontend, journey flows, tests) SHALL be updated in the same PR. Per AC-25, AC-26.

#### Scenario: UserDTO contains person projection
- **WHEN** a `UserDTO` is serialized from a user record
- **THEN** it SHALL contain a `person` field of type `PersonDTO` with human data
- **AND** it SHALL NOT contain `user_category_id`
- **AND** it SHALL NOT contain flat `user_profile` fields (photo, dob, etc. at the top level)

#### Scenario: Breaking change flagged for consumers
- **WHEN** the frontend or any in-repo consumer reads a `UserDTO`
- **THEN** it SHALL access human data via `user.person.*`
- **AND** SHALL NOT attempt to read `user.user_category_id` or `user.user_profile.*`

---

### REQ-USER-AC-02: Student Enrollment Reference (Modified — FK repoint setup)

C-05 `StudentEnrollment.student_id` SHALL repoint from `app_user.id` to `student.id` (the `student` domain entity, which links to `person` via `student.person_id`). The `student` table lands in the **next capability** (domain split); this revamp's migration delivers `person` as the anchor so the repoint is possible. The validation rule "Student must exist in `app_user` table" / "Student must have 'Student' role" SHALL change to reference the `student` domain entity. Per D3a, AC-16.

> **Note:** The actual `student` table creation and FK repoint execution belong to the next capability (domain split). This delta records the **setup**: `person` is delivered as the anchor; the repoint is declared. The `student`/`employee` tables do not exist yet.

#### Scenario: Enrollment references student domain entity (after domain split)
- **GIVEN** the domain split has created the `student` table linked to `person`
- **WHEN** a student is enrolled in a section
- **THEN** `student_enrollment.student_id` SHALL reference `student.id`
- **AND** the `student` SHALL link to a `person` via `student.person_id`
- **AND** the validation SHALL verify the student exists in the `student` table (NOT `app_user`)

#### Scenario: Repoint setup delivered by this revamp
- **WHEN** this revamp's migration is applied
- **THEN** `person` SHALL exist as the anchor
- **AND** the domain split (next capability) SHALL be able to create `student` with `student.person_id` → `person.id` and repoint `student_enrollment.student_id` → `student.id`

---

### REQ-FE-USR-01: Users List/Create/Edit/Transition (Modified — person projection)

The Users screen SHALL list, create, edit, and transition users. Create/edit forms SHALL target human data via the `person` projection (not flat `user_profile` fields). The `user_category` dropdown/filter SHALL be removed. Per AC-25, AC-26.

#### Scenario: Manage users with person projection
- **WHEN** a Client Director or Institution Admin acts on the Users screen
- **THEN** they can list, create, edit, and transition users within their scope
- **AND** profile fields are sourced from the `person` projection
- **AND** there is no `user_category` dropdown or filter

---

### REQ-FE-USR-02: Profile View and Edit (Modified — person-backed)

The user profile view SHALL display and edit profile fields sourced from the `person` entity. The generic `user_profile`-keyed-by-`app_user` fields SHALL no longer be used; human data comes from `person`. Per AC-12, AC-25.

#### Scenario: Edit profile fields via person
- **WHEN** a user opens another user's profile
- **THEN** they can view and edit the profile fields sourced from `person`

---

### REQ-FE-USR-05: Lookups-Driven Reference Dropdowns (Modified — user-category removed)

Reference dropdowns on user forms SHALL be populated from the lookups API. The `user-category` dropdown SHALL be **removed** (no `user_category` table exists after this revamp). Other reference dropdowns (role, institution-type, org-unit-type, legal-entity-type) SHALL remain. Per AC-26.

#### Scenario: No user-category dropdown
- **WHEN** a user form renders
- **THEN** there SHALL be no user-category dropdown
- **AND** other reference dropdowns (role, institution-type, etc.) SHALL be populated from the lookups API

---

## REMOVED Requirements

### REQ-IUM-REM-01: user_category_id Column and All Dependent Logic

`app_user.user_category_id` SHALL be dropped. All requirements, DTOs, filters, and creation/list logic keyed on `user_category_id` SHALL be removed. Role-in-institution SHALL be derived from `person→student`/`employee` projections + `role_assignment` + the `is_platform_owner` flag. No singular human classification SHALL exist anywhere. Per D6a, AC-11.

#### Scenario: user_category_id gone
- **WHEN** the `app_user` table schema is inspected
- **THEN** there SHALL be no `user_category_id` column
- **AND** no DTO, filter, or creation logic SHALL reference `user_category_id`

#### Scenario: GET /api/v1/lookups/user-categories removed
- **WHEN** the lookups API surface is inspected
- **THEN** the `user-categories` endpoint SHALL NOT exist
- **AND** no frontend dropdown SHALL reference user categories

---

### REQ-IUM-REM-02: user_profile Table

The `user_profile` table SHALL be dropped. Its columns (photo, DOB, contact, etc.) SHALL live on `person`. The generic-profile-keyed-by-`app_user` requirements SHALL be removed. Domain-extended data stays on `student_profile`/`employee_profile` (domain-split ADR D7 — those land in the next capability). Per D6a, AC-12.

#### Scenario: user_profile table gone
- **WHEN** the database schema is inspected
- **THEN** there SHALL be no `user_profile` table
- **AND** the human data columns SHALL exist on `person`

---

### REQ-IUM-REM-03: user_category='Learner' ⟺ Student-Link Invariant

The proxy-classification invariant that linked `user_category = 'Learner'` to student status SHALL be retired entirely. No module (including fees) SHALL use a `user_category` value as a student test. Per D6a, AC-14.

#### Scenario: No Learner proxy check
- **WHEN** any module determines whether a user is a student
- **THEN** it SHALL NOT check `user_category = 'Learner'`
- **AND** student status SHALL be derived from the `student` domain entity (next capability) or `role_assignment`

---

### REQ-IUM-REM-04: Platform Owner Discovery by user_category

No code SHALL discover Platform Owners by `user_category = 'Executive Leadership'` or any `user_category` value. PO discovery SHALL use the `is_platform_owner` flag/claim exclusively. Per D6a, AC-13.

#### Scenario: No category-based PO discovery
- **WHEN** the codebase is searched for Platform Owner discovery logic
- **THEN** no code SHALL reference `user_category` for PO detection
- **AND** PO discovery SHALL use `is_platform_owner` exclusively

---

## Creation Flow and Account-Parent Model (Resolved — D3f: person and user_account coexist)

> **Q8 RESOLVED as D3f:** `person` and `user_account` are **two distinct entities**. `user_account` (creation ADR D12) is the account parent — the shared FK target for `role_assignment.user_id` and `login_attempt.user_id`. `person` is the human anchor (demographics, status, projections). Accounts link to `person` via nullable `person_id` FKs. `person.id` is **independent** of the account UUID (a person may have zero or multiple accounts). Roles are account-scoped (D8 + D3b); `role_assignment`/`login_attempt`/RLS `current_user_id` all target `user_account.id`, unchanged.

### REQ-IUM-Q8-01: Creation Flow Insert Order (Resolved — D3f)

The user-creation flow SHALL insert in this order: (1) `person` (independent UUID, human data), (2) `user_account` (D12 shared-UUID parent), (3) the child account row (`app_user` or `client_user`) carrying the `user_account` UUID, (4) set `app_user.person_id` / `client_user.person_id` → the `person.id`. The `user_account`-first invariant from D12 is preserved for the account-parent insert; `person` is inserted before it (person is the outermost anchor). A `person` MAY also be created with NO account (bulk-import / pre-login scenario) — in that case only `person` is inserted. `person.id` is independent of the account UUID. Per D3f, D12, D3a, AC-20.

#### Scenario: Institution user creation insert order
- **GIVEN** a Client Director creates an institution user via `POST /api/v1/users`
- **WHEN** the creation transaction executes
- **THEN** `person` SHALL be inserted first (independent UUID, human data)
- **AND** `user_account` SHALL be inserted second (shared-UUID parent per D12)
- **AND** `app_user` SHALL be inserted third carrying the `user_account` UUID
- **AND** `app_user.person_id` SHALL be set → the `person.id`

#### Scenario: CD bootstrap creation insert order
- **GIVEN** the Platform Owner bootstraps a CD
- **WHEN** the creation transaction executes
- **THEN** `person` SHALL be inserted first, then `user_account`, then `client_user` with the `user_account` UUID
- **AND** `client_user.person_id` SHALL be set → the `person.id`

#### Scenario: Person created with no account (pre-login / bulk-import)
- **GIVEN** an admin creates a `person` for a pre-login student record
- **WHEN** the creation executes
- **THEN** only `person` SHALL be inserted (no `user_account`, no account row)
- **AND** the `person` is fully valid and may receive an account later

#### Scenario: person.id is independent of account UUID
- **GIVEN** a person with one or multiple accounts
- **WHEN** the UUIDs are compared
- **THEN** `person.id` SHALL NOT equal the account UUID
- **AND** the account UUID is the `user_account.id` (D12 shared-UUID pattern, preserved)

---

### REQ-IUM-Q8-02: role_assignment.user_id FK Target (Resolved — D3f)

`role_assignment.user_id` SHALL target `user_account.id` (UNCHANGED). Roles are account-scoped (D8 + D3b); a cross-institution human has different roles per account, so the FK referent stays on the account parent, not `person`. The Casbin loader query text is unchanged. Per D3f, D8, D3b.

#### Scenario: role_assignment targets user_account (unchanged)
- **WHEN** a `role_assignment` row is inspected
- **THEN** `role_assignment.user_id` SHALL reference `user_account.id`
- **AND** SHALL NOT reference `person.id`
- **AND** the Casbin loader query SHALL be unchanged

---

### REQ-IUM-Q8-03: login_attempt.user_id FK Target (Resolved — D3f)

`login_attempt.user_id` SHALL target `user_account.id` (UNCHANGED). A credential (account) attempts login, not a human; the FK referent stays on the account parent. Per D3f, D12.

#### Scenario: login_attempt targets user_account (unchanged)
- **WHEN** a `login_attempt` row is inspected
- **THEN** `login_attempt.user_id` SHALL reference `user_account.id`
- **AND** SHALL NOT reference `person.id`
