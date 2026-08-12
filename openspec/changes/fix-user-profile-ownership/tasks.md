# Tasks — UserProfile Self-Service & Ownership

## Phase 0: Schema Migration

### T-01: UserProfile FK → user_account
**File:** `backend/migrations/versions/018_user_profile_user_account_fk.py`
**Change:** Drop `user_profile.user_id` FK to `app_user.id`, add FK to `user_account.id`
**Verify:** `alembic upgrade head` succeeds

### T-02: Add user_profile permissions
**File:** Same migration
**Change:** 
- `user_profile.create` for Admin, client_director, institution_admin
- `user_profile.update` for Teacher, Staff, Student, Parent
- `user_profile.read` for Teacher, Staff, Student, Parent
**Verify:** All roles have correct user_profile permissions

## Phase 1: Route Changes

### T-03: Update create_profile route
**File:** `backend/kernel/user/routes/profiles.py`
**Change:** Use inline `check_permission` with `owner_id=user_id`
**Verify:** CD can create profile for student; Teacher cannot

### T-04: Update get_profile route
**File:** `backend/kernel/user/routes/profiles.py`
**Change:** Pass `owner_id=user_id` to `check_permission`
**Verify:** Student can read own profile; Student cannot read another's

### T-05: Update update_profile route
**File:** `backend/kernel/user/routes/profiles.py`
**Change:** Pass `owner_id=user_id` to `check_permission`
**Verify:** Teacher can update own profile; Teacher cannot update another's

## Phase 2: Testing

### T-06: Update test files
**File:** `backend/tests/test_c04_authz.py`
**Change:** Add test cases for profile ownership
**Verify:** All tests pass
