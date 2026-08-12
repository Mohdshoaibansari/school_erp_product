## Purpose

This delta spec modifies C-02 Identity & User Management to fix UserProfile ownership and self-service issues discovered during Flow 16 testing. It addresses the UserProfile FK constraint, adds ownership enforcement on profile endpoints, and implements self-creation logic without requiring `user_profile.create` permission.

**Delta type:** MODIFIED
**Base spec:** `openspec/changes/archive/2026-07-11-add-c02-identity-user-management/specs/identity-user-management/spec.md`
**Decisional source:** D13 (UserProfile self-service & ownership)

---

## Requirements

### Requirement: UserProfile FK to user_account

`UserProfile.user_id` SHALL reference `user_account.id` instead of `app_user.id`. This enables CD users (stored in `client_user`) to have UserProfile records. The migration SHALL backfill existing profile `user_id` values to match `user_account` rows (same pattern as D12).

Trace: D13-c, AC-1, AC-8.

#### Scenario: UserProfile references user_account
- **WHEN** the database schema for `user_profile` is inspected
- **THEN** the `user_id` column has a FK constraint referencing `user_account.id` (not `app_user.id`)

#### Scenario: CD user can have a UserProfile
- **WHEN** a CD user (in `client_user`) creates a UserProfile
- **THEN** the UserProfile is created successfully with `user_id` referencing the CD user's `user_account.id`

#### Scenario: Existing profiles are backfilled
- **WHEN** migration 018 is applied
- **THEN** all existing `user_profile.user_id` values are updated to reference the corresponding `user_account.id` (matching by email or other unique identifier)

### Requirement: Ownership Enforcement on Profile Endpoints

Profile endpoints (`GET`, `POST`, `PATCH /api/v1/users/{id}/profile`) SHALL pass `owner_id=user_id` to `require_permission`. The `require_permission` dependency SHALL enforce an ownership check: if `owner_id != ctx.user_id` and the user does NOT have admin-level bypass (institution scope), the endpoint SHALL return HTTP 403.

Trace: D13-a, AC-5, AC-6, AC-7.

#### Scenario: User can read their own profile
- **WHEN** a Teacher (user_id=UUID-A) calls `GET /api/v1/users/UUID-A/profile`
- **THEN** the endpoint passes `owner_id=UUID-A` to `require_permission`, ownership check passes, and the profile is returned

#### Scenario: User cannot read another user's profile
- **WHEN** a Teacher (user_id=UUID-A) calls `GET /api/v1/users/UUID-B/profile`
- **THEN** the endpoint passes `owner_id=UUID-B` to `require_permission`, ownership check fails (`owner_id != ctx.user_id`), and returns HTTP 403

#### Scenario: Admin can read any profile in their institution
- **WHEN** an Admin (user_id=UUID-X, institution_id=SchoolA) calls `GET /api/v1/users/UUID-A/profile` (where UUID-A is at SchoolA)
- **THEN** the endpoint passes `owner_id=UUID-A` to `require_permission`, ownership check fails but Admin has institution scope bypass, and the profile is returned

#### Scenario: User can update their own profile
- **WHEN** a Teacher (user_id=UUID-A) calls `PATCH /api/v1/users/UUID-A/profile` with `{date_of_birth, gender, blood_group}`
- **THEN** the endpoint passes `owner_id=UUID-A` to `require_permission`, ownership check passes, and the profile is updated

#### Scenario: User cannot update another user's profile
- **WHEN** a Teacher (user_id=UUID-A) calls `PATCH /api/v1/users/UUID-B/profile`
- **THEN** the endpoint passes `owner_id=UUID-B` to `require_permission`, ownership check fails, and returns HTTP 403

### Requirement: Self-Creation Without user_profile.create Permission

`POST /api/v1/users/{id}/profile` SHALL allow self-creation without requiring `user_profile.create` permission. The endpoint SHALL pass `owner_id=user_id` to `require_permission`. If `owner_id == ctx.user_id`, the creation proceeds regardless of `user_profile.create` permission. Admin users with `user_profile.create` permission can create profiles on behalf of other users.

Trace: D13-b, AC-4.

#### Scenario: Student creates their own profile
- **WHEN** a Student (user_id=UUID-A) calls `POST /api/v1/users/UUID-A/profile` with `{date_of_birth, gender, blood_group}`
- **THEN** the endpoint passes `owner_id=UUID-A` to `require_permission`, ownership check passes (self-creation), and the profile is created (HTTP 201)

#### Scenario: Student cannot create profile for another user
- **WHEN** a Student (user_id=UUID-A) calls `POST /api/v1/users/UUID-B/profile`
- **THEN** the endpoint passes `owner_id=UUID-B` to `require_permission`, ownership check fails (`owner_id != ctx.user_id`), Student lacks `user_profile.create` permission, and returns HTTP 403

#### Scenario: Admin creates profile for a student
- **WHEN** an Admin (user_id=UUID-X) calls `POST /api/v1/users/UUID-A/profile` with `{date_of_birth, gender, blood_group}`
- **THEN** the endpoint passes `owner_id=UUID-A` to `require_permission`, ownership check fails but Admin has `user_profile.create` permission with institution scope, and the profile is created (HTTP 201)

#### Scenario: Duplicate profile creation rejected
- **WHEN** a user calls `POST /api/v1/users/{id}/profile` and a UserProfile already exists for that user_id
- **THEN** the endpoint returns HTTP 409 Conflict

### Requirement: Profile Endpoint Authorization

All profile endpoints SHALL declare `Depends(require_permission("user_profile", action, ...))` with the appropriate action (`create`, `read`, `update`) and `owner_id` parameter.

Trace: D13, AC-4, AC-5, AC-6.

#### Scenario: POST endpoint requires user_profile.create or self-ownership
- **WHEN** `POST /api/v1/users/{id}/profile` is called
- **THEN** the endpoint passes `owner_id=user_id` to `require_permission("user_profile", "create", owner_id=user_id)`

#### Scenario: GET endpoint requires user_profile.read or self-ownership
- **WHEN** `GET /api/v1/users/{id}/profile` is called
- **THEN** the endpoint passes `owner_id=user_id` to `require_permission("user_profile", "read", owner_id=user_id)`

#### Scenario: PATCH endpoint requires user_profile.update or self-ownership
- **WHEN** `PATCH /api/v1/users/{id}/profile` is called
- **THEN** the endpoint passes `owner_id=user_id` to `require_permission("user_profile", "update", owner_id=user_id)`
