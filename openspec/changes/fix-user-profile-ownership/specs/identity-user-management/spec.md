# identity-user-management — Delta Spec (UserProfile Self-Service)

> **Change:** `fix-user-profile-ownership`
> **Domain:** C-02 Identity & User Management
> **Delta type:** MODIFIED

---

## MODIFIED Requirements

### Requirement: UserProfile FK references user_account (D13)

`UserProfile.user_id` FK SHALL reference `user_account.id` instead of `app_user.id`. This enables CD users (in `client_user`) to have profiles.

#### Scenario: CD user can have a profile
- WHEN a CD user (in `client_user`) has a UserProfile created
- THEN the `user_id` FK to `user_account.id` is satisfied
- AND the profile is queryable

### Requirement: Any user can update their own profile (D13)

The `PATCH /api/v1/users/{user_id}/profile` endpoint SHALL pass `owner_id=user_id` to `check_permission`. This restricts updates to:
- The user themselves (`owner_id == ctx.user_id`)
- Admin/CD/institution_admin (institution scope bypass)

#### Scenario: Teacher updates own profile
- WHEN a Teacher calls `PATCH /api/v1/users/{teacher_id}/profile` with their own user_id
- THEN the ownership check passes (`owner_id == ctx.user_id`)
- AND the profile is updated

#### Scenario: Teacher cannot update another user's profile
- WHEN a Teacher calls `PATCH /api/v1/users/{other_teacher_id}/profile`
- THEN the ownership check fails (`owner_id != ctx.user_id`)
- AND the Teacher does NOT have institution scope → 403

#### Scenario: Admin can update any profile
- WHEN an Admin calls `PATCH /api/v1/users/{any_user_id}/profile`
- THEN the ownership check fails but Admin has institution scope → passes

### Requirement: Any user can read their own profile (D13)

The `GET /api/v1/users/{user_id}/profile` endpoint SHALL pass `owner_id=user_id` to `check_permission`.

#### Scenario: Student reads own profile
- WHEN a Student calls `GET /api/v1/users/{student_id}/profile`
- THEN the ownership check passes
- AND the profile is returned

### Requirement: Admin can create profiles on behalf of users (D13)

The `POST /api/v1/users/{user_id}/profile` endpoint SHALL use inline `check_permission` with `owner_id=user_id`.

#### Scenario: CD creates profile for student
- WHEN a CD calls `POST /api/v1/users/{student_id}/profile`
- THEN the CD has `user_profile.create` with tenant scope
- AND the profile is created

#### Scenario: Teacher cannot create profile for another user
- WHEN a Teacher calls `POST /api/v1/users/{other_user_id}/profile`
- THEN the Teacher does NOT have `user_profile.create` → 403
