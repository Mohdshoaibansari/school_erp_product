## Purpose

This delta spec modifies C-02 Identity & User Management to fix UserProfile ownership and self-service issues discovered during Flow 16 testing. It implements a two-tier permission model: self-service (Stage 3 bypass for own profile) and admin management (`user_profile.admin` permission for Admin/CD/institution_admin).

**Delta type:** MODIFIED
**Base spec:** `openspec/changes/archive/2026-07-11-add-c02-identity-user-management/specs/identity-user-management/spec.md`
**Decisional source:** D13 (UserProfile self-service & admin management)

---

## Requirements

### Requirement: UserProfile FK to user_account

`UserProfile.user_id` SHALL reference `user_account.id` instead of `app_user.id`. This enables CD users (stored in `client_user`) to have UserProfile records. The migration SHALL backfill existing profile `user_id` values to match `user_account` rows (same pattern as D12).

Trace: D13-c, AC-1, AC-7.

#### Scenario: UserProfile references user_account
- **WHEN** the database schema for `user_profile` is inspected
- **THEN** the `user_id` column has a FK constraint referencing `user_account.id` (not `app_user.id`)

#### Scenario: CD user can have a UserProfile
- **WHEN** a CD user (in `client_user`) creates a UserProfile
- **THEN** the UserProfile is created successfully with `user_id` referencing the CD user's `user_account.id`

#### Scenario: Existing profiles are backfilled
- **WHEN** migration 018 is applied
- **THEN** all existing `user_profile.user_id` values have corresponding `user_account` rows

### Requirement: Self-Service Profile Management (Stage 3 Bypass)

Any authenticated user SHALL be able to create, read, and update their own profile via Stage 3 self-access bypass. When `owner_id == ctx.user_id`, the authorization check passes immediately without consulting Casbin. No `user_profile.create`, `user_profile.read`, or `user_profile.update` permission is required for self-service operations.

Trace: D13-a, AC-3.

#### Scenario: Teacher creates own profile
- **WHEN** a Teacher (user_id=UUID-A) calls `POST /api/v1/users/UUID-A/profile` with `{date_of_birth, gender, blood_group}`
- **THEN** Stage 3 check passes (`owner_id == ctx.user_id`), profile is created (HTTP 201)

#### Scenario: Student reads own profile
- **WHEN** a Student (user_id=UUID-A) calls `GET /api/v1/users/UUID-A/profile`
- **THEN** Stage 3 check passes (`owner_id == ctx.user_id`), profile is returned (HTTP 200)

#### Scenario: Parent updates own profile
- **WHEN** a Parent (user_id=UUID-A) calls `PATCH /api/v1/users/UUID-A/profile` with `{phone_number}`
- **THEN** Stage 3 check passes (`owner_id == ctx.user_id`), profile is updated (HTTP 200)

#### Scenario: Any role can self-service
- **WHEN** any authenticated user (Teacher, Staff, Student, Parent, Admin, CD, institution_admin) accesses their own profile endpoint
- **THEN** the operation succeeds regardless of Casbin permissions

### Requirement: Admin Profile Management (`user_profile.admin`)

Admin, client_director, and institution_admin SHALL have a `user_profile.admin` permission that allows them to create, read, and update any user's profile within their scope (institution or tenant). This permission is checked at Stage 4 (Casbin) when `owner_id != ctx.user_id`.

Trace: D13-a, AC-2, AC-4.

#### Scenario: Admin creates profile for student
- **WHEN** an Admin (user_id=UUID-X, institution_id=SchoolA) calls `POST /api/v1/users/UUID-A/profile`
- **THEN** Stage 3 fails (`owner_id != ctx.user_id`), Stage 4 Casbin checks `user_profile.admin` at institution scope → passes, profile is created (HTTP 201)

#### Scenario: CD reads any profile at tenant scope
- **WHEN** a client_director (user_id=UUID-X) calls `GET /api/v1/users/UUID-A/profile`
- **THEN** Stage 3 fails, Stage 4 Casbin checks `user_profile.admin` at tenant scope → passes, profile is returned (HTTP 200)

#### Scenario: Admin updates any profile in institution
- **WHEN** an Admin (user_id=UUID-X, institution_id=SchoolA) calls `PATCH /api/v1/users/UUID-A/profile`
- **THEN** Stage 3 fails, Stage 4 Casbin checks `user_profile.admin` → passes, profile is updated (HTTP 200)

#### Scenario: institution_admin has admin access
- **WHEN** an institution_admin calls any profile endpoint for another user
- **THEN** Stage 4 Casbin checks `user_profile.admin` at institution scope → passes

### Requirement: Non-Admin Cross-User Access Denied

Users without `user_profile.admin` permission SHALL NOT be able to create, read, or update another user's profile. When `owner_id != ctx.user_id` and the user lacks `user_profile.admin`, the endpoint SHALL return HTTP 403.

Trace: D13-a, AC-5.

#### Scenario: Teacher cannot read another teacher's profile
- **WHEN** a Teacher (user_id=UUID-A) calls `GET /api/v1/users/UUID-B/profile`
- **THEN** Stage 3 fails (`owner_id != ctx.user_id`), Stage 4 Casbin checks `user_profile.admin` → Teacher has no such permission, returns HTTP 403

#### Scenario: Student cannot update another student's profile
- **WHEN** a Student (user_id=UUID-A) calls `PATCH /api/v1/users/UUID-B/profile`
- **THEN** Stage 3 fails, Stage 4 Casbin fails, returns HTTP 403

#### Scenario: Staff cannot create profile for another user
- **WHEN** a Staff (user_id=UUID-A) calls `POST /api/v1/users/UUID-B/profile`
- **THEN** Stage 3 fails, Stage 4 Casbin fails, returns HTTP 403

### Requirement: Duplicate Profile Rejection

`POST /api/v1/users/{id}/profile` SHALL return HTTP 409 Conflict if a UserProfile already exists for the given `user_id`.

Trace: AC-4.

#### Scenario: Duplicate profile creation rejected
- **WHEN** a user calls `POST /api/v1/users/{id}/profile` and a UserProfile already exists for that `user_id`
- **THEN** the endpoint returns HTTP 409 Conflict
